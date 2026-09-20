"""
Servicio para métricas y estadísticas del Dashboard de StyleStore (v6 Punto 1).
Soporta filtrado por sucursal (para encargados de sucursal y administradores).
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.orden_venta import OrdenVenta
from app.models.stock_inventario import StockInventario
from app.models.cliente import Cliente
from app.models.reserva import Reserva
from app.models.envio import Envio
from app.models.cambio_devolucion import CambioDevolucion
from app.models.sucursal import Sucursal


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_stats(self, sucursal_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcula todas las métricas operativas del dashboard según la sucursal o global."""
        today = date.today()
        first_day_month = today.replace(day=1)

        # 1. Ventas
        ventas_query = self.db.query(OrdenVenta).filter(OrdenVenta.estado != "anulado")
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

        # Total histórico de ingresos
        total_ingresos = sum((float(v.total) for v in ventas_query.all()), 0.0)
        total_ventas_count = ventas_query.count()

        # 2. Inventario y Stock Crítico
        stock_query = self.db.query(StockInventario)
        if sucursal_id:
            stock_query = stock_query.filter(StockInventario.sucursal_id == sucursal_id)

        total_stock_unidades = self.db.query(func.coalesce(func.sum(StockInventario.cantidad), 0))
        if sucursal_id:
            total_stock_unidades = total_stock_unidades.filter(StockInventario.sucursal_id == sucursal_id)
        total_stock_unidades = int(total_stock_unidades.scalar() or 0)

        productos_bajo_stock = stock_query.filter(StockInventario.cantidad <= 5).count()

        # 3. Clientes Registrados
        total_clientes = self.db.query(Cliente).count()

        # 4. Reservas Activas / Pendientes
        reservas_query = self.db.query(Reserva).filter(Reserva.estado.in_(["pendiente", "confirmada"]))
        if sucursal_id:
            reservas_query = reservas_query.filter(Reserva.sucursal_id == sucursal_id)
        reservas_activas = reservas_query.count()

        # 5. Envíos Pendientes (Delivery StyleStore)
        envios_query = self.db.query(Envio).filter(Envio.estado.in_(["pendiente", "en_camino"]))
        if sucursal_id:
            envios_query = envios_query.join(OrdenVenta, Envio.orden_venta_id == OrdenVenta.id).filter(
                OrdenVenta.sucursal_id == sucursal_id
            )
        envios_pendientes = envios_query.count()

        # 6. Solicitudes de Cambio / Devolución pendientes
        cambios_query = self.db.query(CambioDevolucion).filter(CambioDevolucion.estado == "pendiente")
        if sucursal_id:
            cambios_query = cambios_query.filter(CambioDevolucion.sucursal_id == sucursal_id)
        cambios_pendientes = cambios_query.count()

        # Lista de sucursales para el selector en el dashboard
        sucursales = self.db.query(Sucursal).filter(Sucursal.active == True).all()
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

        return {
            "sucursal_id": sucursal_id,
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
            "inventario": {
                "total_unidades": total_stock_unidades,
                "bajo_stock": productos_bajo_stock,
            },
            "total_clientes": total_clientes,
            "reservas_activas": reservas_activas,
            "envios_pendientes": envios_pendientes,
            "cambios_pendientes": cambios_pendientes,
            "ventas_recientes": ventas_recientes,
            "sucursales": sucursales_data,
        }
