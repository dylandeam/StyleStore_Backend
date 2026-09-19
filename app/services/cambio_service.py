"""
Servicio de Cambios y Devoluciones de Prendas (v6 Punto 9).
Regla: Solicitud permitida únicamente dentro de los 7 días posteriores a la fecha de compra.
"""
from datetime import date, datetime, timedelta, time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.cambio_devolucion import CambioDevolucion
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.stock_inventario import StockInventario
from app.models.producto_color import ProductoColor
from app.models.cliente import Cliente
from app.models.user import User
from app.services.notificacion_service import NotificacionService


class CambioService:
    def __init__(self, db: Session):
        self.db = db

    def solicitar_cambio_devolucion(
        self,
        user: User,
        orden_venta_id: int,
        detalle_venta_id: int,
        tipo: str,
        motivo: str,
        sucursal_id: int,
        fecha_programada: date,
        descripcion_problema: str,
        hora_programada: Optional[time] = None,
        producto_nuevo_codigo: Optional[str] = None,
        talla_nueva_id: Optional[int] = None,
        color_nuevo_id: Optional[int] = None,
    ) -> CambioDevolucion:
        """Registra una solicitud de cambio o devolución validando el límite estricto de 7 días."""
        # 1. Validar cliente
        cliente = self.db.query(Cliente).filter(Cliente.user_id == user.id).first()
        if not cliente:
            raise HTTPException(status_code=400, detail="El usuario no tiene un perfil de cliente.")

        # 2. Validar que la orden pertenezca al cliente
        orden = self.db.query(OrdenVenta).filter(
            OrdenVenta.id == orden_venta_id, OrdenVenta.codigo_cliente == cliente.codigo
        ).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden de venta no encontrada o no pertenece a este usuario.")

        # 3. Validar los 7 días de límite
        fecha_compra = orden.fecha
        limite = fecha_compra + timedelta(days=7)
        if date.today() > limite:
            raise HTTPException(
                status_code=400,
                detail=f"El plazo de garantía para cambios o devoluciones es de 7 días posteriores a la compra. Tu compra fue el {fecha_compra.strftime('%d/%m/%Y')} y expiró el {limite.strftime('%d/%m/%Y')}."
            )

        # 4. Validar detalle de venta
        detalle = self.db.query(DetalleVenta).filter(
            DetalleVenta.id == detalle_venta_id, DetalleVenta.orden_venta_id == orden.id
        ).first()
        if not detalle:
            raise HTTPException(status_code=404, detail="El artículo no pertenece a la orden indicada.")

        # 5. Crear la solicitud
        solicitud = CambioDevolucion(
            orden_venta_id=orden.id,
            detalle_venta_id=detalle.id,
            tipo=tipo,
            motivo=motivo,
            sucursal_id=sucursal_id,
            fecha_programada=fecha_programada,
            hora_programada=hora_programada,
            producto_nuevo_codigo=producto_nuevo_codigo,
            talla_nueva_id=talla_nueva_id,
            color_nuevo_id=color_nuevo_id,
            descripcion_problema=descripcion_problema,
            estado="pendiente",
        )
        self.db.add(solicitud)
        self.db.commit()
        self.db.refresh(solicitud)

        # Notificar in-app al cliente de su solicitud recibida
        notif_srv = NotificacionService(self.db)
        notif_srv.crear_notificacion(
            user_id=user.id,
            tipo="cambio_devolucion",
            titulo="Solicitud de Cambio/Devolución Recibida",
            mensaje=f"Hemos recibido tu solicitud de {tipo} para el producto de tu orden {orden.ticket_numero or orden.id}. Un encargado revisará tu caso.",
            url_accion="/cuenta/mis-compras",
            enviar_email=True,
        )

        return solicitud

    def listar_solicitudes(
        self,
        sucursal_id: Optional[int] = None,
        estado: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CambioDevolucion]:
        """Lista solicitudes para el panel de administración / encargado."""
        q = self.db.query(CambioDevolucion).options(
            joinedload(CambioDevolucion.orden_venta).joinedload(OrdenVenta.cliente).joinedload(Cliente.user),
            joinedload(CambioDevolucion.detalle_venta),
            joinedload(CambioDevolucion.sucursal),
            joinedload(CambioDevolucion.producto_nuevo),
            joinedload(CambioDevolucion.talla_nueva),
            joinedload(CambioDevolucion.color_nuevo),
        )
        if sucursal_id:
            q = q.filter(CambioDevolucion.sucursal_id == sucursal_id)
        if estado:
            q = q.filter(CambioDevolucion.estado == estado)

        return q.order_by(CambioDevolucion.id.desc()).offset(offset).limit(limit).all()

    def listar_mis_solicitudes(self, user: User) -> List[CambioDevolucion]:
        """Lista las solicitudes del cliente autenticado."""
        cliente = self.db.query(Cliente).filter(Cliente.user_id == user.id).first()
        if not cliente:
            return []

        return (
            self.db.query(CambioDevolucion)
            .join(OrdenVenta, CambioDevolucion.orden_venta_id == OrdenVenta.id)
            .filter(OrdenVenta.codigo_cliente == cliente.codigo)
            .options(
                joinedload(CambioDevolucion.orden_venta),
                joinedload(CambioDevolucion.detalle_venta),
                joinedload(CambioDevolucion.sucursal),
                joinedload(CambioDevolucion.producto_nuevo),
                joinedload(CambioDevolucion.talla_nueva),
                joinedload(CambioDevolucion.color_nuevo),
            )
            .order_by(CambioDevolucion.id.desc())
            .all()
        )

    def responder_solicitud(
        self,
        solicitud_id: int,
        nuevo_estado: str,  # 'aceptada' | 'rechazada'
        respuesta_encargado: str,
    ) -> CambioDevolucion:
        """El encargado o administrador aprueba o rechaza la solicitud y notifica al cliente."""
        solicitud = self.db.query(CambioDevolucion).options(
            joinedload(CambioDevolucion.orden_venta).joinedload(OrdenVenta.cliente).joinedload(Cliente.user)
        ).filter(CambioDevolucion.id == solicitud_id).first()
        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

        solicitud.estado = nuevo_estado
        solicitud.respuesta_encargado = respuesta_encargado
        self.db.commit()

        # Notificar al cliente
        if solicitud.orden_venta and solicitud.orden_venta.cliente and solicitud.orden_venta.cliente.user:
            user = solicitud.orden_venta.cliente.user
            titulo = f"Solicitud de {solicitud.tipo.title()} {nuevo_estado.upper()}"
            mensaje = f"Tu solicitud para la orden {solicitud.orden_venta.ticket_numero or solicitud.orden_venta_id} ha sido {nuevo_estado}. Mensaje del encargado: {respuesta_encargado}"
            notif_srv = NotificacionService(self.db)
            notif_srv.crear_notificacion(
                user_id=user.id,
                tipo="cambio_devolucion",
                titulo=titulo,
                mensaje=mensaje,
                url_accion="/cuenta/mis-compras",
                enviar_email=True,
            )

        return solicitud

    def completar_en_caja(
        self,
        solicitud_id: int,
        reponer_prenda_original: bool = True,
        nuevo_stock_inventario_id: Optional[int] = None,
    ) -> CambioDevolucion:
        """
        Completa el cambio/devolución en caja física.
        Ajusta inventario: si reponer_prenda_original es True, incrementa stock devuelto.
        Si se entrega nueva prenda, descuenta su stock.
        """
        solicitud = self.db.query(CambioDevolucion).options(
            joinedload(CambioDevolucion.detalle_venta)
        ).filter(CambioDevolucion.id == solicitud_id).first()
        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")

        # 1. Reposición de prenda original (si no está dañada)
        if reponer_prenda_original and solicitud.detalle_venta and solicitud.detalle_venta.stock_inventario_id:
            stk = self.db.query(StockInventario).filter(
                StockInventario.id == solicitud.detalle_venta.stock_inventario_id
            ).first()
            if stk:
                stk.cantidad += 1

        # 2. Descuento de nueva prenda si fue cambio
        if solicitud.tipo == "cambio" and nuevo_stock_inventario_id:
            nuevo_stk = self.db.query(StockInventario).filter(
                StockInventario.id == nuevo_stock_inventario_id
            ).first()
            if nuevo_stk and nuevo_stk.cantidad > 0:
                nuevo_stk.cantidad -= 1

        solicitud.estado = "completada"
        self.db.commit()
        return solicitud
