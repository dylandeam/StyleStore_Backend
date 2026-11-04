"""
Servicio para métricas y estadísticas del Dashboard de StyleStore (v6 Punto 1).
Soporta filtrado por sucursal (para encargados de sucursal y administradores).
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import case, func, or_

from app.models.orden_venta import OrdenVenta
from app.models.pago import Pago
from app.models.stock_inventario import StockInventario
from app.models.cliente import Cliente
from app.models.reserva import Reserva
from app.models.envio import Envio
from app.models.cambio_devolucion import CambioDevolucion
from app.models.sucursal import Sucursal
from app.models.user import User
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.categoria import Categoria
from app.core.exceptions import ForbiddenException
from app.services.tenant_scope import scope_by_empresa, scope_by_sucursal


class DashboardService:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user

    def _scope_branch(self, query, column):
        return scope_by_sucursal(query, self.db, self.current_user, column)

    def available_indicators(self) -> list[str]:
        role = str(self.current_user.role or "").strip().lower()
        if role == "cliente":
            return ["historial_compras"]
        if role in {"cajero", "vendedor", "repartidor"}:
            return ["ventas_sucursal", "historial_compras"]
        if role in {"administrador", "administrador_tenant", "admin_tenant", "encargado", "encargado_sucursal"}:
            return ["ventas_sucursal", "stock_categoria", "historial_compras"]
        return []

    def get_indicator_detail(self, indicator: str, sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        """Detalle navegable para los indicadores habilitados por rol y sucursal."""
        if indicator not in self.available_indicators():
            raise ForbiddenException("Este indicador no está disponible para tu rol.")
        if indicator == "ventas_sucursal":
            return self._sales_by_branch(sucursal_id)
        if indicator == "stock_categoria":
            return self._stock_by_category(sucursal_id)
        return self._purchase_history(sucursal_id)

    def _sales_by_branch(self, sucursal_id: Optional[int]) -> Dict[str, Any]:
        query = (
            self.db.query(
                Sucursal.id,
                Sucursal.name,
                func.count(OrdenVenta.id).label("cantidad"),
                func.coalesce(func.sum(OrdenVenta.total), 0).label("monto"),
            )
            .join(OrdenVenta, OrdenVenta.sucursal_id == Sucursal.id)
            .filter(~OrdenVenta.estado.in_(["anulado", "cancelada"]))
        )
        query = self._scope_branch(query, Sucursal.id)
        if sucursal_id:
            query = query.filter(Sucursal.id == sucursal_id)
        rows = query.group_by(Sucursal.id, Sucursal.name).order_by(func.sum(OrdenVenta.total).desc()).all()
        data = [
            {"sucursal": row.name, "ventas": int(row.cantidad), "monto": round(float(row.monto or 0), 2)}
            for row in rows
        ]
        return {
            "indicador": "ventas_sucursal",
            "titulo": "Ventas por sucursal",
            "descripcion": "Comparación de ventas válidas dentro de las sucursales permitidas para tu rol.",
            "grafico": [{"label": row["sucursal"], "value": row["monto"]} for row in data],
            "columnas": [
                {"key": "sucursal", "label": "Sucursal"},
                {"key": "ventas", "label": "Ventas"},
                {"key": "monto", "label": "Monto (Bs)"},
            ],
            "filas": data,
        }

    def _stock_by_category(self, sucursal_id: Optional[int]) -> Dict[str, Any]:
        query = (
            self.db.query(
                Categoria.nombre,
                func.coalesce(func.sum(StockInventario.cantidad), 0).label("unidades"),
                func.count(StockInventario.id).label("variantes"),
                func.sum(case((StockInventario.cantidad <= 5, 1), else_=0)).label("criticos"),
            )
            .join(ProductoColor, ProductoColor.id == StockInventario.producto_color_id)
            .join(Producto, Producto.codigo == ProductoColor.producto_codigo)
            .join(Categoria, Categoria.id == Producto.categoria_id)
        )
        query = self._scope_branch(query, StockInventario.sucursal_id)
        if sucursal_id:
            query = query.filter(StockInventario.sucursal_id == sucursal_id)
        rows = query.group_by(Categoria.id, Categoria.nombre).order_by(func.sum(StockInventario.cantidad).desc()).all()
        data = [
            {
                "categoria": row.nombre,
                "unidades": int(row.unidades or 0),
                "variantes": int(row.variantes or 0),
                "criticos": int(row.criticos or 0),
            }
            for row in rows
        ]
        return {
            "indicador": "stock_categoria",
            "titulo": "Stock por categoría",
            "descripcion": "Unidades, variantes y alertas de bajo stock agrupadas por categoría.",
            "grafico": [{"label": row["categoria"], "value": row["unidades"]} for row in data],
            "columnas": [
                {"key": "categoria", "label": "Categoría"},
                {"key": "unidades", "label": "Unidades"},
                {"key": "variantes", "label": "Variantes"},
                {"key": "criticos", "label": "Stock crítico"},
            ],
            "filas": data,
        }

    def _purchase_history(self, sucursal_id: Optional[int]) -> Dict[str, Any]:
        query = self.db.query(OrdenVenta).filter(~OrdenVenta.estado.in_(["anulado", "cancelada"]))
        role = str(self.current_user.role or "").strip().lower()
        if role == "cliente":
            query = query.join(Cliente, Cliente.codigo == OrdenVenta.codigo_cliente).filter(
                Cliente.user_id == self.current_user.id
            )
        else:
            query = self._scope_branch(query, OrdenVenta.sucursal_id)
        if sucursal_id:
            query = query.filter(OrdenVenta.sucursal_id == sucursal_id)
        orders = query.order_by(OrdenVenta.fecha.desc(), OrdenVenta.id.desc()).limit(50).all()
        data = [
            {
                "orden": order.ticket_numero or f"ORD-{order.id:04d}",
                "fecha": order.fecha.isoformat() if order.fecha else "",
                "sucursal": order.sucursal.name if order.sucursal else "Sin sucursal",
                "metodo": (order.metodo_pago or "Sin registrar").upper(),
                "estado": order.estado,
                "total": round(float(order.total or 0), 2),
            }
            for order in orders
        ]
        by_date: dict[str, float] = {}
        for row in data:
            by_date[row["fecha"]] = round(by_date.get(row["fecha"], 0) + row["total"], 2)
        return {
            "indicador": "historial_compras",
            "titulo": "Historial de compras" if role == "cliente" else "Historial de ventas",
            "descripcion": "Últimas operaciones visibles para tu rol y alcance de sucursal.",
            "grafico": [{"label": label, "value": value} for label, value in sorted(by_date.items())[-10:]],
            "columnas": [
                {"key": "orden", "label": "Orden"},
                {"key": "fecha", "label": "Fecha"},
                {"key": "sucursal", "label": "Sucursal"},
                {"key": "metodo", "label": "Pago"},
                {"key": "estado", "label": "Estado"},
                {"key": "total", "label": "Total (Bs)"},
            ],
            "filas": data,
        }

    def get_dashboard_stats(self, sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcula todas las métricas operativas del dashboard según la sucursal o global."""
        today = date.today()
        first_day_month = today.replace(day=1)

        # 1. Ventas (excluir anuladas/canceladas)
        ventas_query = self.db.query(OrdenVenta).filter(
            ~OrdenVenta.estado.in_(["anulado", "cancelada"])
        )
        ventas_query = self._scope_branch(ventas_query, OrdenVenta.sucursal_id)
        if sucursal_id:
            ventas_query = ventas_query.filter(OrdenVenta.sucursal_id == sucursal_id)

        # Ventas hoy
        ventas_hoy_q = ventas_query.filter(OrdenVenta.fecha == today)
        ventas_hoy_count = ventas_hoy_q.count()
        ventas_hoy_monto = sum((float(v.total) for v in ventas_hoy_q.all()), 0.0)

        # Ventas mes
        ventas_mes_q = ventas_query.filter(OrdenVenta.fecha >= first_day_month)
        ventas_mes_count = ventas_mes_q.count()
        ventas_mes_monto = sum((float(v.total) for v in ventas_mes_q.all()), 0.0)

        # Total histórico de ingresos y cantidad
        all_ventas = ventas_query.all()
        total_ingresos = sum((float(v.total) for v in all_ventas), 0.0)
        total_ventas_count = len(all_ventas)

        # Desglose de pagos por método (usando OrdenVenta.metodo_pago)
        desglose_efectivo = 0.0
        desglose_paypal = 0.0
        desglose_qr = 0.0
        desglose_otro = 0.0

        for v in all_ventas:
            metodo = (v.metodo_pago or "efectivo").lower().strip()
            monto = float(v.total)
            if metodo in ("efectivo", "en caja", "cash"):
                desglose_efectivo += monto
            elif metodo in ("paypal", "en linea", "en_linea", "online"):
                desglose_paypal += monto
            elif metodo in ("qr", "qr_mostrador", "transferencia"):
                desglose_qr += monto
            else:
                desglose_efectivo += monto  # default to efectivo

        # 2. Inventario y Stock Crítico
        stock_query = self.db.query(StockInventario)
        stock_query = self._scope_branch(stock_query, StockInventario.sucursal_id)
        if sucursal_id:
            stock_query = stock_query.filter(StockInventario.sucursal_id == sucursal_id)

        total_stock_unidades = self.db.query(func.coalesce(func.sum(StockInventario.cantidad), 0))
        total_stock_unidades = self._scope_branch(total_stock_unidades, StockInventario.sucursal_id)
        if sucursal_id:
            total_stock_unidades = total_stock_unidades.filter(StockInventario.sucursal_id == sucursal_id)
        total_stock_unidades = int(total_stock_unidades.scalar() or 0)

        productos_bajo_stock = stock_query.filter(StockInventario.cantidad <= 5).count()

        # 3. Clientes Registrados
        clientes_query = self.db.query(Cliente).join(User, Cliente.user_id == User.id)
        total_clientes = scope_by_empresa(
            clientes_query, self.current_user, User.empresa_id
        ).count()

        # 4. Reservas Activas / Pendientes
        reservas_activas_query = self.db.query(Reserva).filter(
            Reserva.estado.in_(["pendiente", "confirmada"])
        )
        reservas_activas_query = self._scope_branch(reservas_activas_query, Reserva.sucursal_id)
        if sucursal_id:
            reservas_activas_query = reservas_activas_query.filter(Reserva.sucursal_id == sucursal_id)
        reservas_activas = reservas_activas_query.count()

        # Reservas vencidas
        reservas_vencidas_query = self.db.query(Reserva).filter(
            Reserva.estado.in_(["vencida", "cancelada"])
        )
        reservas_vencidas_query = self._scope_branch(reservas_vencidas_query, Reserva.sucursal_id)
        if sucursal_id:
            reservas_vencidas_query = reservas_vencidas_query.filter(Reserva.sucursal_id == sucursal_id)
        reservas_vencidas = reservas_vencidas_query.count()

        # 5. Envíos Pendientes (Delivery StyleStore)
        envios_query = self.db.query(Envio).join(
            OrdenVenta, Envio.orden_venta_id == OrdenVenta.id
        ).filter(Envio.estado.in_(["pendiente", "en_camino"]))
        envios_query = self._scope_branch(envios_query, OrdenVenta.sucursal_id)
        if sucursal_id:
            envios_query = envios_query.filter(OrdenVenta.sucursal_id == sucursal_id)
        envios_pendientes = envios_query.count()

        # 6. Solicitudes de Cambio / Devolución pendientes
        cambios_query = self.db.query(CambioDevolucion).filter(CambioDevolucion.estado == "pendiente")
        cambios_query = self._scope_branch(cambios_query, CambioDevolucion.sucursal_id)
        if sucursal_id:
            cambios_query = cambios_query.filter(CambioDevolucion.sucursal_id == sucursal_id)
        cambios_pendientes = cambios_query.count()

        # Lista de sucursales para el selector en el dashboard
        sucursales = scope_by_empresa(
            self.db.query(Sucursal), self.current_user, Sucursal.empresa_id
        ).filter(Sucursal.active == True).all()
        sucursales_data = [{"id": s.id, "nombre": s.nombre, "ciudad": s.ciudad} for s in sucursales]

        # Últimas 5 ventas recientes
        recientes_q = ventas_query.order_by(OrdenVenta.id.desc()).limit(5).all()
        ventas_recientes = []
        for r in recientes_q:
            cli_nom = "Cliente General"
            if r.cliente and hasattr(r.cliente, "user") and r.cliente.user:
                cli_nom = f"{r.cliente.user.name} {r.cliente.user.apellido or ''}".strip()
            elif r.cliente and hasattr(r.cliente, "nombre"):
                cli_nom = r.cliente.nombre or "Cliente General"

            ventas_recientes.append({
                "id": r.id,
                "ticket_numero": r.ticket_numero or f"ORD-{r.id:04d}",
                "fecha": r.fecha.strftime("%d/%m/%Y") if r.fecha else "",
                "cliente": cli_nom,
                "total": float(r.total),
                "metodo_pago": (r.metodo_pago or "EFECTIVO").upper(),
                "estado": r.estado,
            })

        # =====================================================
        # Respuesta con estructura que el frontend espera:
        #   stats.ventas.total_recaudado
        #   stats.ventas.cantidad_ventas
        #   stats.ventas.desglose_pagos.efectivo / paypal / en_linea / qr
        #   stats.inventario.items_criticos / total_existencias
        #   stats.reservas.activas / vencidas
        #   stats.cambios.pendientes
        # También mantiene claves legacy por compatibilidad.
        # =====================================================
        return {
            "sucursal_id": sucursal_id,
            # --- Estructura anidada que el frontend consume ---
            "ventas": {
                "total_recaudado": round(total_ingresos, 2),
                "cantidad_ventas": total_ventas_count,
                "ventas_hoy": ventas_hoy_count,
                "monto_hoy": round(ventas_hoy_monto, 2),
                "ventas_mes": ventas_mes_count,
                "monto_mes": round(ventas_mes_monto, 2),
                "desglose_pagos": {
                    "efectivo": round(desglose_efectivo, 2),
                    "paypal": round(desglose_paypal, 2),
                    "en_linea": round(desglose_paypal, 2),
                    "qr": round(desglose_qr, 2),
                },
            },
            "inventario": {
                "items_criticos": productos_bajo_stock,
                "total_existencias": total_stock_unidades,
                "total_unidades": total_stock_unidades,
                "bajo_stock": productos_bajo_stock,
            },
            "reservas": {
                "activas": reservas_activas,
                "vencidas": reservas_vencidas,
            },
            "cambios": {
                "pendientes": cambios_pendientes,
            },
            # --- Claves legacy para compatibilidad ---
            "ventas_hoy": {
                "cantidad": ventas_hoy_count,
                "monto": round(ventas_hoy_monto, 2),
            },
            "ventas_mes": {
                "cantidad": ventas_mes_count,
                "monto": round(ventas_mes_monto, 2),
            },
            "total_ingresos": round(total_ingresos, 2),
            "total_ventas": total_ventas_count,
            "total_clientes": total_clientes,
            "reservas_activas": reservas_activas,
            "envios_pendientes": envios_pendientes,
            "cambios_pendientes": cambios_pendientes,
            "ventas_recientes": ventas_recientes,
            "sucursales": sucursales_data,
        }
