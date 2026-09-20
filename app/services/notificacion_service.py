"""
Servicio de Notificaciones y Suscripciones (v6 Punto 5).
Gestiona notificaciones in-app y envío por correo electrónico.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.notificacion import Notificacion, SuscripcionProximamente, SuscripcionStock
from app.models.user import User
from app.models.proximamente import Proximamente
from app.models.stock_inventario import StockInventario
from app.core.email import send_notification_email


class NotificacionService:
    def __init__(self, db: Session):
        self.db = db

    def crear_notificacion(
        self,
        user_id: int,
        tipo: str,
        titulo: str,
        mensaje: str,
        url_accion: Optional[str] = None,
        enviar_email: bool = True,
    ) -> Notificacion:
        """Crea una notificación in-app y opcionalmente envía correo electrónico al usuario."""
        notif = Notificacion(
            user_id=user_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            url_accion=url_accion,
            leida=False,
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)

        if enviar_email:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                send_notification_email(
                    to_email=user.email,
                    subject=f"StyleStore: {titulo}",
                    title=titulo,
                    message=mensaje,
                    action_url=url_accion,
                )

        return notif

    def listar_notificaciones_usuario(
        self, user_id: int, limit: int = 30, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Lista las notificaciones de un usuario ordenadas de más recientes a más antiguas."""
        notifs = (
            self.db.query(Notificacion)
            .filter(Notificacion.user_id == user_id)
            .order_by(desc(Notificacion.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": n.id,
                "tipo": n.tipo,
                "titulo": n.titulo,
                "mensaje": n.mensaje,
                "leida": n.leida,
                "url_accion": n.url_accion,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ]

    def contar_no_leidas(self, user_id: int) -> int:
        """Cuenta las notificaciones no leídas de un usuario."""
        return (
            self.db.query(Notificacion)
            .filter(Notificacion.user_id == user_id, Notificacion.leida == False)
            .count()
        )

    def marcar_como_leida(self, notificacion_id: int, user_id: int) -> bool:
        """Marca una notificación específica como leída."""
        notif = (
            self.db.query(Notificacion)
            .filter(Notificacion.id == notificacion_id, Notificacion.user_id == user_id)
            .first()
        )
        if not notif:
            return False
        notif.leida = True
        self.db.commit()
        return True

    def marcar_todas_leidas(self, user_id: int) -> int:
        """Marca todas las notificaciones no leídas de un usuario como leídas."""
        updated = (
            self.db.query(Notificacion)
            .filter(Notificacion.user_id == user_id, Notificacion.leida == False)
            .update({"leida": True})
        )
        self.db.commit()
        return updated

    # ==========================================
    # Suscripciones Próximamente y Stock
    # ==========================================

    def suscribir_proximamente(self, user_id: int, proximamente_id: int) -> Dict[str, Any]:
        """Suscribe a un usuario para recibir aviso de un artículo de Próximamente."""
        existente = (
            self.db.query(SuscripcionProximamente)
            .filter(
                SuscripcionProximamente.user_id == user_id,
                SuscripcionProximamente.proximamente_id == proximamente_id,
            )
            .first()
        )
        if existente:
            return {"status": "ya_suscrito", "mensaje": "Ya estás suscrito a este artículo."}

        sub = SuscripcionProximamente(user_id=user_id, proximamente_id=proximamente_id)
        self.db.add(sub)
        self.db.commit()
        return {"status": "suscrito", "mensaje": "Te notificaremos por correo e in-app en cuanto esté disponible."}

    def suscribir_stock(self, user_id: int, stock_inventario_id: int) -> Dict[str, Any]:
        """Suscribe a un usuario para recibir aviso cuando se reponga el stock de una prenda."""
        existente = (
            self.db.query(SuscripcionStock)
            .filter(
                SuscripcionStock.user_id == user_id,
                SuscripcionStock.stock_inventario_id == stock_inventario_id,
            )
            .first()
        )
        if existente:
            return {"status": "ya_suscrito", "mensaje": "Ya estás suscrito para alertas de stock de este producto."}

        sub = SuscripcionStock(user_id=user_id, stock_inventario_id=stock_inventario_id)
        self.db.add(sub)
        self.db.commit()
        return {"status": "suscrito", "mensaje": "Te avisaremos de inmediato cuando se reponga stock."}

    def notificar_llegada_proximamente(self, proximamente_id: int, producto_codigo: Optional[str] = None) -> int:
        """Dispara notificaciones masivas a los clientes suscritos a un artículo que ya llegó."""
        subs = (
            self.db.query(SuscripcionProximamente)
            .filter(SuscripcionProximamente.proximamente_id == proximamente_id)
            .all()
        )
        item = self.db.query(Proximamente).filter(Proximamente.id == proximamente_id).first()
        nombre_item = item.nombre if (item and item.nombre) else "El artículo que esperabas"
        url = f"/catalogo/producto/{producto_codigo}" if producto_codigo else "/catalogo"
        count = len(subs)

        for s in subs:
            self.crear_notificacion(
                user_id=s.user_id,
                tipo="proximamente",
                titulo="¡Ya disponible en StyleStore!",
                mensaje=f"Buenas noticias: '{nombre_item}' ya se encuentra disponible en tienda y catálogo. ¡No te quedes sin el tuyo!",
                url_accion=url,
                enviar_email=True,
            )
            self.db.delete(s)
        self.db.commit()
        return count

    def notificar_reposicion_stock(self, stock_inventario_id: int):
        """Dispara notificaciones a los clientes suscritos a un stock que se acaba de reponer."""
        subs = (
            self.db.query(SuscripcionStock)
            .filter(SuscripcionStock.stock_inventario_id == stock_inventario_id)
            .all()
        )
        stock = self.db.query(StockInventario).filter(StockInventario.id == stock_inventario_id).first()
        prod_nom = "Prenda"
        codigo = ""
        if stock and stock.producto_color and stock.producto_color.producto:
            prod_nom = stock.producto_color.producto.nombre
            codigo = stock.producto_color.producto.codigo

        for s in subs:
            self.crear_notificacion(
                user_id=s.user_id,
                tipo="stock_disponible",
                titulo="¡Stock disponible en StyleStore!",
                mensaje=f"Tenemos stock disponible para '{prod_nom}'. Ya puedes adquirirlo o apartarlo en sucursal.",
                url_accion=f"/catalogo/producto/{codigo}" if codigo else "/catalogo",
                enviar_email=True,
            )
            self.db.delete(s)
        self.db.commit()
