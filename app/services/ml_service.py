"""Modelos ML reproducibles, livianos y aislados por tenant."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
import math
import random
from typing import Any

from sqlalchemy.orm import Session

from app.models.orden_venta import OrdenVenta
from app.models.sucursal import Sucursal
from app.models.user import User
from app.services.tenant_scope import effective_empresa_id, scope_by_sucursal


SEED = 20261021
FEATURES = ("tendencia", "mes", "dia_semana", "fin_semana", "promocion")


def generate_synthetic_sales(rows: int = 730, seed: int = SEED) -> list[dict[str, Any]]:
    """Genera dos años de demanda diaria con señal estacional y ruido controlado."""
    rng = random.Random(seed)
    start = date(2024, 1, 1)
    result = []
    for index in range(rows):
        day = start + timedelta(days=index)
        weekend = int(day.weekday() >= 5)
        promotion = int(index % 17 in (0, 1, 2))
        seasonal = 36 * math.sin((2 * math.pi * day.month) / 12)
        revenue = 520 + index * 0.42 + seasonal + weekend * 145 + promotion * 210 + rng.gauss(0, 28)
        transactions = max(1, round(revenue / (72 + rng.uniform(-8, 8))))
        result.append({
            "fecha": day.isoformat(), "tendencia": index / max(rows - 1, 1),
            "mes": day.month, "dia_semana": day.weekday(), "fin_semana": weekend,
            "promocion": promotion, "transacciones": transactions,
            "ingresos": round(max(revenue, 0), 2),
        })
    return result


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[i][:] + [vector[i]] for i in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column] or 1e-12
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [augmented[row][i] - factor * augmented[column][i] for i in range(size + 1)]
    return [augmented[i][-1] for i in range(size)]


def _features(row: dict[str, Any]) -> list[float]:
    return [1.0, float(row["tendencia"]), float(row["mes"]) / 12,
            float(row["dia_semana"]) / 6, float(row["fin_semana"]), float(row["promocion"])]


def _predict(coefficients: list[float], row: dict[str, Any]) -> float:
    return sum(a * b for a, b in zip(coefficients, _features(row)))


@lru_cache(maxsize=1)
def train_supervised_model() -> dict[str, Any]:
    dataset = generate_synthetic_sales()
    split = int(len(dataset) * 0.8)
    train, test = dataset[:split], dataset[split:]
    dimensions = len(FEATURES) + 1
    xtx = [[0.0] * dimensions for _ in range(dimensions)]
    xty = [0.0] * dimensions
    for row in train:
        x, y = _features(row), float(row["ingresos"])
        for i in range(dimensions):
            xty[i] += x[i] * y
            for j in range(dimensions):
                xtx[i][j] += x[i] * x[j]
    for index in range(1, dimensions):
        xtx[index][index] += 0.001
    coefficients = _solve(xtx, xty)
    predictions = [_predict(coefficients, row) for row in test]
    actual = [float(row["ingresos"]) for row in test]
    mae = sum(abs(a - p) for a, p in zip(actual, predictions)) / len(actual)
    mean = sum(actual) / len(actual)
    ss_res = sum((a - p) ** 2 for a, p in zip(actual, predictions))
    ss_tot = sum((a - mean) ** 2 for a in actual) or 1
    return {
        "tipo": "regresion_lineal_ridge", "objetivo": "ingresos_diarios",
        "features": list(FEATURES), "seed": SEED, "filas_entrenamiento": len(train),
        "filas_prueba": len(test), "mae": round(mae, 2), "r2": round(1 - ss_res / ss_tot, 4),
        "coefficients": coefficients,
        "synthetic_mean": sum(float(row["ingresos"]) for row in dataset[-30:]) / 30,
    }


def _distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _kmeans(points: list[list[float]], k: int = 3, iterations: int = 50) -> tuple[list[list[float]], list[int]]:
    ordered = sorted(points, key=sum)
    centers = [ordered[round((len(ordered) - 1) * ratio)][:] for ratio in (0.15, 0.5, 0.85)]
    labels = [-1] * len(points)
    for _ in range(iterations):
        next_labels = [min(range(k), key=lambda idx: _distance(point, centers[idx])) for point in points]
        next_centers = []
        for cluster in range(k):
            members = [point for point, label in zip(points, next_labels) if label == cluster]
            next_centers.append([sum(point[col] for point in members) / len(members) for col in range(len(points[0]))] if members else centers[cluster])
        if next_labels == labels:
            centers, labels = next_centers, next_labels
            break
        centers, labels = next_centers, next_labels
    return centers, labels


@lru_cache(maxsize=1)
def train_unsupervised_model() -> dict[str, Any]:
    rng = random.Random(SEED)
    points = []
    for _ in range(120):
        bases = ((1.5, 80, 80), (5, 260, 35), (12, 850, 12))[rng.randrange(3)]
        points.append([max(0, rng.gauss(bases[0], .8)), max(0, rng.gauss(bases[1], 35)), max(0, rng.gauss(bases[2], 12))])
    maxima = [max(point[i] for point in points) or 1 for i in range(3)]
    normalized = [[point[i] / maxima[i] for i in range(3)] for point in points]
    centers, labels = _kmeans(normalized)
    ordered = sorted(range(3), key=lambda idx: centers[idx][0] + centers[idx][1] - centers[idx][2])
    names = {ordered[0]: "ocasional", ordered[1]: "frecuente", ordered[2]: "alto_valor"}
    return {
        "tipo": "kmeans", "features": ["frecuencia", "valor_monetario", "recencia_dias"],
        "seed": SEED, "k": 3, "filas_entrenamiento": len(points), "centers": centers,
        "maxima": maxima, "names": names,
        "distribucion_sintetica": {names[i]: labels.count(i) for i in range(3)},
    }


class MLService:
    def __init__(self, db: Session, current_user: User):
        self.db, self.current_user = db, current_user

    def _orders(self, sucursal_id: int | None = None) -> list[OrdenVenta]:
        empresa_id = effective_empresa_id(self.current_user)
        query = scope_by_sucursal(
            self.db.query(OrdenVenta).filter(~OrdenVenta.estado.in_(["anulado", "cancelada"])),
            self.db, self.current_user, OrdenVenta.sucursal_id,
        )
        if sucursal_id:
            allowed_query = self.db.query(Sucursal.id).filter(Sucursal.id == sucursal_id)
            if empresa_id is not None:
                allowed_query = allowed_query.filter(Sucursal.empresa_id == empresa_id)
            allowed = allowed_query.first()
            if not allowed:
                return []
            query = query.filter(OrdenVenta.sucursal_id == sucursal_id)
        return query.all()

    def insights(self, sucursal_id: int | None = None) -> dict[str, Any]:
        supervised, unsupervised = train_supervised_model(), train_unsupervised_model()
        completed = [order for order in self._orders(sucursal_id) if order.fecha and order.total is not None]
        recent = [float(order.total) for order in completed if order.fecha >= date.today() - timedelta(days=30)]
        calibration = ((sum(recent) / 30) / supervised["synthetic_mean"]) if recent else 0.0
        forecasts = []
        for offset in range(1, 8):
            target = date.today() + timedelta(days=offset)
            row = {"tendencia": (730 + offset) / 730, "mes": target.month, "dia_semana": target.weekday(), "fin_semana": int(target.weekday() >= 5), "promocion": 0}
            forecasts.append({"fecha": target.isoformat(), "ingresos_estimados": round(max(0, _predict(supervised["coefficients"], row) * calibration), 2)})
        by_client: dict[str, list[OrdenVenta]] = defaultdict(list)
        for order in completed:
            client_key = order.codigo_cliente or "anonimo"
            by_client[client_key].append(order)
        segments = {"ocasional": 0, "frecuente": 0, "alto_valor": 0}
        for client_orders in by_client.values():
            latest = max(order.fecha for order in client_orders)
            raw = [float(len(client_orders)), sum(float(order.total) for order in client_orders), float(max((date.today() - latest).days, 0))]
            point = [raw[i] / unsupervised["maxima"][i] for i in range(3)]
            label = min(range(3), key=lambda idx: _distance(point, unsupervised["centers"][idx]))
            segments[unsupervised["names"][label]] += 1
        return {
            "tenant_id": effective_empresa_id(self.current_user), "sucursal_id": sucursal_id,
            "generado_en": date.today().isoformat(),
            "modelo_supervisado": {key: supervised[key] for key in ("tipo", "objetivo", "features", "seed", "filas_entrenamiento", "filas_prueba", "mae", "r2")},
            "pronostico_7_dias": forecasts,
            "total_estimado_7_dias": round(sum(item["ingresos_estimados"] for item in forecasts), 2),
            "modelo_no_supervisado": {key: unsupervised[key] for key in ("tipo", "features", "seed", "k", "filas_entrenamiento", "distribucion_sintetica")},
            "segmentos_clientes": segments, "clientes_analizados": len(by_client),
            "muestra_real_ordenes": len(completed),
            "nota": "Estimación analítica; no sustituye decisiones comerciales ni garantiza ventas futuras.",
        }

    def predictive_stock_alerts(
        self,
        sucursal_id: int | None = None,
        criticidad: str | None = None,
        dias_horizonte: int = 30,
    ) -> dict[str, Any]:
        """Calcula el riesgo predictivo de agotamiento de stock y reposición sugerida (REQ-068)."""
        from sqlalchemy import func
        from app.models.stock_inventario import StockInventario
        from app.models.producto_color import ProductoColor
        from app.models.producto import Producto
        from app.models.talla import Talla
        from app.models.color import Color
        from app.models.orden_venta import DetalleVenta

        query = (
            self.db.query(
                StockInventario,
                Producto.nombre.label("producto_nombre"),
                Producto.codigo.label("producto_codigo"),
                Sucursal.name.label("sucursal_nombre"),
                Color.nombre.label("color_nombre"),
                Talla.nombre.label("talla_nombre"),
            )
            .join(Sucursal, StockInventario.sucursal_id == Sucursal.id)
            .join(ProductoColor, StockInventario.producto_color_id == ProductoColor.id)
            .join(Producto, ProductoColor.producto_codigo == Producto.codigo)
            .join(Color, ProductoColor.color_id == Color.id)
            .join(Talla, StockInventario.talla_id == Talla.id)
        )
        empresa_id = effective_empresa_id(self.current_user)
        if empresa_id is not None:
            query = query.filter(Sucursal.empresa_id == empresa_id)
        if sucursal_id:
            query = query.filter(StockInventario.sucursal_id == sucursal_id)

        stocks = query.all()

        since_date = date.today() - timedelta(days=dias_horizonte)
        sales_query = (
            self.db.query(
                DetalleVenta.stock_inventario_id,
                func.sum(DetalleVenta.cantidad).label("unidades_vendidas"),
            )
            .join(OrdenVenta, DetalleVenta.orden_venta_id == OrdenVenta.id)
            .join(Sucursal, OrdenVenta.sucursal_id == Sucursal.id)
            .filter(
                ~OrdenVenta.estado.in_(["anulado", "cancelada"]),
                OrdenVenta.fecha >= since_date,
            )
        )
        if empresa_id is not None:
            sales_query = sales_query.filter(Sucursal.empresa_id == empresa_id)
        if sucursal_id:
            sales_query = sales_query.filter(OrdenVenta.sucursal_id == sucursal_id)

        sales_by_stock = {
            row[0]: int(row[1])
            for row in sales_query.group_by(DetalleVenta.stock_inventario_id).all()
            if row[0] is not None
        }

        items = []
        criticas_count = 0
        altas_count = 0
        medias_count = 0

        for stock, prod_nombre, prod_codigo, suc_nombre, col_nombre, tal_nombre in stocks:
            cant = int(stock.cantidad or 0)
            vendidas = sales_by_stock.get(stock.id, 0)
            vel = round(vendidas / max(dias_horizonte, 1), 2)

            if vel > 0:
                cobertura = round(cant / vel, 1)
            else:
                cobertura = 999.0 if cant > 0 else 0.0

            if cant == 0 or (vel > 0 and cobertura <= 3.0):
                nivel = "CRITICO"
                criticas_count += 1
            elif vel > 0 and cobertura <= 7.0:
                nivel = "ALTO"
                altas_count += 1
            elif (vel > 0 and cobertura <= 15.0) or (cant <= 3 and vel > 0):
                nivel = "MEDIO"
                medias_count += 1
            else:
                nivel = "NORMAL"

            if criticidad and criticidad.upper() != nivel:
                continue

            if nivel in ("CRITICO", "ALTO", "MEDIO"):
                demanda_30d = round(vel * 30)
                reposicion = max(10, demanda_30d - cant) if demanda_30d > cant else 10
            else:
                reposicion = 0

            items.append({
                "stock_id": stock.id,
                "producto": prod_nombre,
                "codigo": prod_codigo,
                "sucursal": suc_nombre,
                "color": col_nombre,
                "talla": tal_nombre,
                "stock_actual": cant,
                "velocidad_diaria": vel,
                "dias_cobertura": cobertura,
                "criticidad": nivel,
                "reposicion_sugerida": reposicion,
            })

        order_rank = {"CRITICO": 0, "ALTO": 1, "MEDIO": 2, "NORMAL": 3}
        items.sort(key=lambda x: (order_rank.get(x["criticidad"], 4), x["dias_cobertura"]))

        return {
            "tenant_id": empresa_id,
            "sucursal_id": sucursal_id,
            "generado_en": date.today().isoformat(),
            "dias_horizonte_analizado": dias_horizonte,
            "total_items_evaluados": len(stocks),
            "alertas_criticas": criticas_count,
            "alertas_altas": altas_count,
            "alertas_medias": medias_count,
            "total_alertas": criticas_count + altas_count + medias_count,
            "items": items,
        }

    def transfer_recommendations(
        self,
        sucursal_id: int | None = None,
        dias_horizonte: int = 30,
    ) -> dict[str, Any]:
        """Propone traspasos entre sucursales usando demanda real y stock disponible.

        La recomendación nunca compromete más de la mitad del stock donante, conserva
        una reserva equivalente a catorce días de su propia demanda y descuenta los
        traspasos pendientes para no sugerir dos veces las mismas unidades.
        """
        from sqlalchemy import func
        from app.models.color import Color
        from app.models.orden_venta import DetalleVenta
        from app.models.producto import Producto
        from app.models.producto_color import ProductoColor
        from app.models.stock_inventario import StockInventario
        from app.models.talla import Talla
        from app.models.traspaso_inventario import TraspasoInventario

        empresa_id = effective_empresa_id(self.current_user)
        stock_rows = (
            self.db.query(
                StockInventario,
                Producto.nombre.label("producto_nombre"),
                Producto.codigo.label("producto_codigo"),
                Sucursal.name.label("sucursal_nombre"),
                Color.nombre.label("color_nombre"),
                Talla.nombre.label("talla_nombre"),
            )
            .join(Sucursal, StockInventario.sucursal_id == Sucursal.id)
            .join(ProductoColor, StockInventario.producto_color_id == ProductoColor.id)
            .join(Producto, ProductoColor.producto_codigo == Producto.codigo)
            .join(Color, ProductoColor.color_id == Color.id)
            .join(Talla, StockInventario.talla_id == Talla.id)
        )
        if empresa_id is not None:
            stock_rows = stock_rows.filter(Sucursal.empresa_id == empresa_id)
        stocks = stock_rows.all()

        since_date = date.today() - timedelta(days=dias_horizonte)
        sales_query = (
            self.db.query(
                DetalleVenta.stock_inventario_id,
                func.coalesce(func.sum(DetalleVenta.cantidad), 0).label("unidades_vendidas"),
            )
            .join(OrdenVenta, DetalleVenta.orden_venta_id == OrdenVenta.id)
            .join(Sucursal, OrdenVenta.sucursal_id == Sucursal.id)
            .filter(
                ~OrdenVenta.estado.in_(["anulado", "cancelada"]),
                OrdenVenta.fecha >= since_date,
            )
        )
        if empresa_id is not None:
            sales_query = sales_query.filter(Sucursal.empresa_id == empresa_id)
        sales_by_stock = {
            int(row[0]): int(row[1] or 0)
            for row in sales_query.group_by(DetalleVenta.stock_inventario_id).all()
            if row[0] is not None
        }

        pending_query = self.db.query(TraspasoInventario).filter(
            TraspasoInventario.estado == "pendiente"
        )
        if empresa_id is not None:
            pending_query = pending_query.filter(TraspasoInventario.empresa_id == empresa_id)
        pending_out: dict[tuple[int, int, int], int] = defaultdict(int)
        pending_in: dict[tuple[int, int, int], int] = defaultdict(int)
        for transfer in pending_query.all():
            variant = (transfer.producto_color_id, transfer.talla_id)
            pending_out[(transfer.sucursal_origen_id, *variant)] += transfer.cantidad
            pending_in[(transfer.sucursal_destino_id, *variant)] += transfer.cantidad

        variants: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for stock, product_name, product_code, branch_name, color_name, size_name in stocks:
            sold = sales_by_stock.get(stock.id, 0)
            velocity = sold / max(dias_horizonte, 1)
            outgoing = pending_out[(stock.sucursal_id, stock.producto_color_id, stock.talla_id)]
            incoming = pending_in[(stock.sucursal_id, stock.producto_color_id, stock.talla_id)]
            effective_stock = max(0, int(stock.cantidad or 0) - outgoing + incoming)
            coverage = effective_stock / velocity if velocity > 0 else (999.0 if effective_stock else 0.0)
            variants[(stock.producto_color_id, stock.talla_id)].append({
                "stock_id": stock.id,
                "producto_color_id": stock.producto_color_id,
                "talla_id": stock.talla_id,
                "sucursal_id": stock.sucursal_id,
                "sucursal": branch_name,
                "producto": product_name,
                "codigo": product_code,
                "color": color_name,
                "talla": size_name,
                "stock_actual": int(stock.cantidad or 0),
                "stock_efectivo": effective_stock,
                "pendiente_salida": outgoing,
                "pendiente_entrada": incoming,
                "vendidas": sold,
                "velocidad": velocity,
                "cobertura": coverage,
            })

        recommendations: list[dict[str, Any]] = []
        priority_rank = {"CRITICA": 0, "ALTA": 1, "MEDIA": 2}
        for variant_rows in variants.values():
            targets = [
                row for row in variant_rows
                if row["velocidad"] > 0
                and row["stock_efectivo"] <= max(3, math.ceil(row["velocidad"] * 15))
                and (sucursal_id is None or row["sucursal_id"] == sucursal_id)
            ]
            targets.sort(key=lambda row: (row["cobertura"], -row["vendidas"]))

            donor_budget: dict[int, int] = {}
            for donor in variant_rows:
                reserve = max(2, math.ceil(donor["velocidad"] * 14))
                donor_budget[donor["stock_id"]] = max(
                    0,
                    min(
                        donor["stock_efectivo"] // 2,
                        donor["stock_efectivo"] - reserve,
                    ),
                )

            for target in targets:
                donors = [
                    donor for donor in variant_rows
                    if donor["sucursal_id"] != target["sucursal_id"]
                    and donor_budget[donor["stock_id"]] > 0
                    and donor["stock_efectivo"] > target["stock_efectivo"]
                    and donor["velocidad"] < target["velocidad"]
                ]
                if not donors:
                    continue
                donors.sort(key=lambda row: (row["velocidad"], -donor_budget[row["stock_id"]]))
                donor = donors[0]
                desired_stock = max(5, math.ceil(target["velocidad"] * 21))
                shortage = max(1, desired_stock - target["stock_efectivo"])
                quantity = min(shortage, donor_budget[donor["stock_id"]])
                if quantity <= 0:
                    continue
                donor_budget[donor["stock_id"]] -= quantity

                coverage = target["cobertura"]
                priority = "CRITICA" if coverage <= 3 or target["stock_efectivo"] == 0 else (
                    "ALTA" if coverage <= 7 else "MEDIA"
                )
                confidence = min(
                    97,
                    55 + min(target["vendidas"], 15) * 2 + (10 if donor["vendidas"] == 0 else 4),
                )
                recommendations.append({
                    "producto_color_id": target["producto_color_id"],
                    "talla_id": target["talla_id"],
                    "producto": target["producto"],
                    "codigo": target["codigo"],
                    "color": target["color"],
                    "talla": target["talla"],
                    "sucursal_origen_id": donor["sucursal_id"],
                    "sucursal_origen": donor["sucursal"],
                    "stock_origen": donor["stock_actual"],
                    "stock_origen_efectivo": donor["stock_efectivo"],
                    "ventas_origen_30d": donor["vendidas"],
                    "sucursal_destino_id": target["sucursal_id"],
                    "sucursal_destino": target["sucursal"],
                    "stock_destino": target["stock_actual"],
                    "stock_destino_efectivo": target["stock_efectivo"],
                    "ventas_destino_30d": target["vendidas"],
                    "dias_cobertura_destino": round(coverage, 1),
                    "cantidad_recomendada": quantity,
                    "prioridad": priority,
                    "confianza_porcentaje": confidence,
                    "explicacion": (
                        f"{target['sucursal']} vendió {target['vendidas']} un. en {dias_horizonte} días "
                        f"y conserva {target['stock_efectivo']}; {donor['sucursal']} vendió "
                        f"{donor['vendidas']} y dispone de {donor['stock_efectivo']}. "
                        f"Mover {quantity} mantiene una reserva operativa en el origen."
                    ),
                })

        recommendations.sort(
            key=lambda item: (
                priority_rank.get(item["prioridad"], 3),
                -item["confianza_porcentaje"],
                item["dias_cobertura_destino"],
            )
        )
        return {
            "tenant_id": empresa_id,
            "sucursal_destino_id": sucursal_id,
            "generado_en": date.today().isoformat(),
            "dias_horizonte_analizado": dias_horizonte,
            "total_variantes_evaluadas": len(variants),
            "total_recomendaciones": len(recommendations),
            "criterio": (
                "Demanda real de 30 días, cobertura objetivo de 21 días, máximo 50% del stock "
                "donante y reserva mínima de 14 días en origen."
            ),
            "items": recommendations,
        }

