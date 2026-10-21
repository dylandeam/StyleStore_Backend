"""
Servicio de Cambios y Devoluciones de Prendas (v6 Punto 9).
Regla: Solicitud permitida únicamente dentro de los 7 días posteriores a la fecha de compra.
"""
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.cambio_devolucion import CambioDevolucion, SaldoFavorCliente, MovimientoSaldoFavor
from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.pago import Pago
from app.models.empresa import Empresa
from app.models.stock_inventario import StockInventario
from app.models.producto_color import ProductoColor
from app.models.cliente import Cliente
from app.models.user import User
from app.services.notificacion_service import NotificacionService
from app.services.tenant_scope import get_scoped_sucursal, scope_by_sucursal


class CambioService:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user

    def _scope_branch(self, query, column):
        return scope_by_sucursal(query, self.db, self.current_user, column)

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
        if orden.sucursal_id:
            get_scoped_sucursal(self.db, user, orden.sucursal_id)
        get_scoped_sucursal(self.db, user, sucursal_id)

        # 3. Validar el plazo configurable del tenant
        fecha_compra = orden.fecha
        if isinstance(fecha_compra, datetime):
            fecha_compra = fecha_compra.date()
        elif isinstance(fecha_compra, str):
            try:
                fecha_compra = date.fromisoformat(fecha_compra[:10])
            except Exception:
                fecha_compra = date.today()
        elif fecha_compra is None:
            fecha_compra = date.today()

        empresa = self.db.query(Empresa).filter(Empresa.id == user.empresa_id).first()
        plazo_dias = empresa.plazo_cambios_dias if empresa else 7
        limite = fecha_compra + timedelta(days=plazo_dias)
        if date.today() > limite:
            raise HTTPException(
                status_code=400,
                detail=f"El plazo de garantía para cambios o devoluciones es de {plazo_dias} días posteriores a la compra. Tu compra fue el {fecha_compra.strftime('%d/%m/%Y')} y expiró el {limite.strftime('%d/%m/%Y')}."
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

        # Notificar in-app al cliente de su solicitud recibida (sin bloquear la petición HTTP)
        notif_srv = NotificacionService(self.db)
        notif_srv.crear_notificacion(
            user_id=user.id,
            tipo="cambio_devolucion",
            titulo="Solicitud de Cambio/Devolución Recibida",
            mensaje=f"Hemos recibido tu solicitud de {tipo} para el producto de tu orden {orden.ticket_numero or orden.id}. Un encargado revisará tu caso.",
            url_accion="/cuenta/mis-compras",
            enviar_email=False,
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
        q = self._scope_branch(q, CambioDevolucion.sucursal_id)
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
        solicitud_query = self.db.query(CambioDevolucion).options(
            joinedload(CambioDevolucion.orden_venta).joinedload(OrdenVenta.cliente).joinedload(Cliente.user)
        )
        solicitud = self._scope_branch(
            solicitud_query, CambioDevolucion.sucursal_id
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
        metodo_pago_diferencia: Optional[str] = None,
        efectivo_recibido: Optional[Decimal] = None,
        metodo_reembolso: Optional[str] = None,
    ) -> CambioDevolucion:
        """Liquida el cambio de forma atómica, emite nota y ajusta inventario/saldo."""
        solicitud_query = self.db.query(CambioDevolucion).options(
            joinedload(CambioDevolucion.detalle_venta),
            joinedload(CambioDevolucion.orden_venta),
        )
        solicitud = self._scope_branch(
            solicitud_query, CambioDevolucion.sucursal_id
        ).filter(CambioDevolucion.id == solicitud_id).first()
        if not solicitud:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
        if solicitud.estado != "aceptada":
            raise HTTPException(status_code=400, detail="Solo se puede completar una solicitud aceptada.")

        detalle = solicitud.detalle_venta
        if not detalle:
            raise HTTPException(status_code=400, detail="La solicitud no tiene una prenda original válida.")
        precio_original = Decimal(detalle.precio_unitario)
        precio_nuevo = Decimal("0.00")
        nuevo_stk = None

        if solicitud.tipo == "cambio":
            if not nuevo_stock_inventario_id:
                # Compatibilidad con solicitudes anteriores: canje por la misma variante.
                nuevo_stock_inventario_id = detalle.stock_inventario_id
            if not nuevo_stock_inventario_id:
                raise HTTPException(status_code=400, detail="Selecciona la nueva prenda que se entregará.")
            nuevo_stk = self._scope_branch(
                self.db.query(StockInventario), StockInventario.sucursal_id
            ).filter(
                StockInventario.id == nuevo_stock_inventario_id,
                StockInventario.sucursal_id == solicitud.sucursal_id,
            ).with_for_update(of=StockInventario).first()
            if not nuevo_stk or nuevo_stk.cantidad <= 0:
                raise HTTPException(status_code=400, detail="La nueva prenda no tiene stock disponible en la sucursal elegida.")
            producto = nuevo_stk.producto_color.producto if nuevo_stk.producto_color else None
            if not producto:
                raise HTTPException(status_code=400, detail="La nueva prenda no es válida.")
            precio_nuevo = Decimal(nuevo_stk.precio_variante if nuevo_stk.precio_variante is not None else producto.precio)

        diferencia = precio_nuevo - precio_original if solicitud.tipo == "cambio" else -precio_original
        monto_adicional = max(diferencia, Decimal("0.00"))
        saldo_generado = abs(min(diferencia, Decimal("0.00"))) if solicitud.tipo == "cambio" else Decimal("0.00")
        monto_reembolsado = precio_original if solicitud.tipo == "devolucion" else Decimal("0.00")
        metodo = (metodo_pago_diferencia or "").lower()
        if monto_adicional > 0:
            if metodo not in {"efectivo", "qr"}:
                raise HTTPException(status_code=400, detail="La diferencia debe cobrarse por efectivo o QR.")
            if metodo == "efectivo" and (efectivo_recibido is None or efectivo_recibido < monto_adicional):
                raise HTTPException(status_code=400, detail="El efectivo recibido no cubre la diferencia del cambio.")
        if solicitud.tipo == "devolucion" and (metodo_reembolso or "").lower() not in {"efectivo", "transferencia"}:
            raise HTTPException(status_code=400, detail="Indica si el reembolso se realizó en efectivo o transferencia.")

        if reponer_prenda_original and detalle.stock_inventario_id:
            stk = self._scope_branch(self.db.query(StockInventario), StockInventario.sucursal_id).filter(
                StockInventario.id == detalle.stock_inventario_id
            ).with_for_update(of=StockInventario).first()
            if stk:
                stk.cantidad += 1

        if nuevo_stk:
            nuevo_stk.cantidad -= 1

        cliente = solicitud.orden_venta.cliente if solicitud.orden_venta else None
        if not cliente or not cliente.user:
            raise HTTPException(status_code=400, detail="No se pudo identificar al cliente del cambio.")

        if saldo_generado > 0:
            empresa_id = solicitud.sucursal.empresa_id
            cuenta = self.db.query(SaldoFavorCliente).filter(
                SaldoFavorCliente.empresa_id == empresa_id,
                SaldoFavorCliente.user_id == cliente.user_id,
            ).with_for_update(of=SaldoFavorCliente).first()
            if not cuenta:
                cuenta = SaldoFavorCliente(empresa_id=empresa_id, user_id=cliente.user_id, saldo=Decimal("0.00"))
                self.db.add(cuenta)
                self.db.flush()
            cuenta.saldo = Decimal(cuenta.saldo) + saldo_generado
            self.db.add(MovimientoSaldoFavor(
                saldo_favor_id=cuenta.id, cambio_devolucion_id=solicitud.id,
                tipo="credito", monto=saldo_generado, saldo_resultante=cuenta.saldo,
                descripcion=f"Saldo por cambio #{solicitud.id} a una prenda de menor precio",
            ))

        now = datetime.now()
        nota = f"NCJ-{now.strftime('%Y%m%d%H%M%S')}-{solicitud.id}"
        orden_ajuste = OrdenVenta(
            fecha=now.date(), estado="pagada", total=monto_adicional, tipo_venta="cambio",
            codigo_cliente=cliente.codigo, sucursal_id=solicitud.sucursal_id,
            ticket_numero=nota,
            metodo_pago=metodo if monto_adicional > 0 else (metodo_reembolso or "saldo_favor"),
        )
        self.db.add(orden_ajuste)
        self.db.flush()
        if nuevo_stk:
            producto = nuevo_stk.producto_color.producto
            self.db.add(DetalleVenta(
                orden_venta_id=orden_ajuste.id, stock_inventario_id=nuevo_stk.id,
                producto_nombre=producto.nombre,
                color_nombre=nuevo_stk.producto_color.color.nombre if nuevo_stk.producto_color.color else None,
                talla_nombre=nuevo_stk.talla.nombre if nuevo_stk.talla else None,
                cantidad=1, precio_unitario=precio_nuevo, subtotal=precio_nuevo,
            ))
        if monto_adicional > 0:
            self.db.add(Pago(
                orden_venta_id=orden_ajuste.id, monto=monto_adicional,
                tipo_pago="en caja", metodo_pago=metodo, estado="aprobado",
            ))

        solicitud.estado = "completada"
        solicitud.nuevo_stock_inventario_id = nuevo_stk.id if nuevo_stk else None
        solicitud.producto_nuevo_codigo = nuevo_stk.producto_color.producto_codigo if nuevo_stk else solicitud.producto_nuevo_codigo
        solicitud.talla_nueva_id = nuevo_stk.talla_id if nuevo_stk else solicitud.talla_nueva_id
        solicitud.color_nuevo_id = nuevo_stk.producto_color.color_id if nuevo_stk else solicitud.color_nuevo_id
        solicitud.precio_original = precio_original
        solicitud.precio_nuevo = precio_nuevo if nuevo_stk else None
        solicitud.monto_adicional = monto_adicional
        solicitud.saldo_favor_generado = saldo_generado
        solicitud.monto_reembolsado = monto_reembolsado
        solicitud.metodo_pago_diferencia = metodo if monto_adicional > 0 else (metodo_reembolso or None)
        solicitud.nota_venta_numero = nota
        solicitud.orden_ajuste_id = orden_ajuste.id
        self.db.commit()
        self.db.refresh(solicitud)
        return solicitud
