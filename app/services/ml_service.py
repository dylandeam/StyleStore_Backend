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
from app.services.tenant_scope import scope_by_sucursal


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
        query = scope_by_sucursal(
            self.db.query(OrdenVenta).filter(~OrdenVenta.estado.in_(["anulado", "cancelada"])),
            self.db, self.current_user, OrdenVenta.sucursal_id,
        )
        if sucursal_id:
            allowed = self.db.query(Sucursal.id).filter(Sucursal.id == sucursal_id, Sucursal.empresa_id == self.current_user.empresa_id).first()
            if not allowed and not self.current_user.is_platform_admin:
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
            by_client[order.codigo_cliente].append(order)
        segments = {"ocasional": 0, "frecuente": 0, "alto_valor": 0}
        for client_orders in by_client.values():
            latest = max(order.fecha for order in client_orders)
            raw = [float(len(client_orders)), sum(float(order.total) for order in client_orders), float(max((date.today() - latest).days, 0))]
            point = [raw[i] / unsupervised["maxima"][i] for i in range(3)]
            label = min(range(3), key=lambda idx: _distance(point, unsupervised["centers"][idx]))
            segments[unsupervised["names"][label]] += 1
        return {
            "tenant_id": self.current_user.empresa_id, "sucursal_id": sucursal_id,
            "generado_en": date.today().isoformat(),
            "modelo_supervisado": {key: supervised[key] for key in ("tipo", "objetivo", "features", "seed", "filas_entrenamiento", "filas_prueba", "mae", "r2")},
            "pronostico_7_dias": forecasts,
            "total_estimado_7_dias": round(sum(item["ingresos_estimados"] for item in forecasts), 2),
            "modelo_no_supervisado": {key: unsupervised[key] for key in ("tipo", "features", "seed", "k", "filas_entrenamiento", "distribucion_sintetica")},
            "segmentos_clientes": segments, "clientes_analizados": len(by_client),
            "muestra_real_ordenes": len(completed),
            "nota": "Estimación analítica; no sustituye decisiones comerciales ni garantiza ventas futuras.",
        }
