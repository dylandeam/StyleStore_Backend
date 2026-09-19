"""
Servicio del Chatbot Inteligente Local para StyleStore (v6 Punto 4).
Opera 100% en local sin APIs de pago ni dependencias externas.
Analiza intenciones del usuario, consulta la base de datos de productos, sucursales,
colecciones y pedidos, y genera respuestas enriquecidas con chips de navegación directa.
"""
import re
import unicodedata
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.sucursal import Sucursal
from app.models.producto import Producto
from app.models.coleccion import Coleccion
from app.models.temporada import Temporada
from app.models.categoria import Categoria
from app.models.reserva import Reserva
from app.models.orden_venta import OrdenVenta
from app.models.cliente import Cliente
from app.models.user import User


def _normalize(text: str) -> str:
    """Normaliza texto eliminando tildes y pasando a minúsculas para comparaciones robustas."""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


class ChatbotService:
    def __init__(self, db: Session):
        self.db = db

    def responder(self, mensaje: str, user: Optional[User] = None) -> Dict[str, Any]:
        """Procesa el mensaje del usuario y devuelve respuesta textual y chips de acción."""
        norm = _normalize(mensaje)

        # 1. Saludos
        if any(w in norm for w in ["hola", "buen dia", "buenas tardes", "buenas noches", "hey", "saludos"]):
            nombre = f", {user.name}" if user else ""
            return {
                "respuesta": f"¡Hola{nombre}! 👋 Bienvenido a StyleStore. ¿En qué puedo colaborarte hoy? Puedes consultarme sobre nuestras sucursales, prendas disponibles, temporadas, estado de tus pedidos o realizar reservas.",
                "chips": [
                    {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                    {"label": "👗 Catálogo de Ropa", "action": "navigate", "route": "/catalogo"},
                    {"label": "📦 Mis Compras", "action": "navigate", "route": "/cuenta/mis-compras"},
                    {"label": "💳 Métodos de Pago", "action": "navigate", "route": "/cuenta/mis-pagos"},
                ],
            }

        # 2. Sucursales / Ubicaciones / Horarios
        if any(w in norm for w in ["sucursal", "sucursales", "donde estan", "ubicacion", "direccion", "tienda fisica", "horario"]):
            sucursales = self.db.query(Sucursal).filter(Sucursal.active == True).all()
            if not sucursales:
                return {
                    "respuesta": "Actualmente estamos actualizando la información de nuestras sucursales físicas.",
                    "chips": [{"label": "Ver Catálogo Online", "action": "navigate", "route": "/catalogo"}],
                }

            lineas = ["🏬 **Nuestras Sucursales StyleStore:**\n"]
            for s in sucursales:
                lineas.append(f"• **{s.nombre}** ({s.ciudad}): {s.direccion} | Tel: {s.telefono or 'No registrado'}")

            lineas.append("\nAtendemos de Lunes a Sábado de 09:00 a 20:00. ¡Te esperamos!")
            return {
                "respuesta": "\n".join(lineas),
                "chips": [
                    {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                    {"label": "👗 Explorar Prendas", "action": "navigate", "route": "/catalogo"},
                ],
            }

        # 3. Métodos de Pago / PayPal / QR / Efectivo
        if any(w in norm for w in ["pago", "pagar", "paypal", "qr", "efectivo", "tarjeta", "metodo"]):
            return {
                "respuesta": "💳 **Métodos de Pago en StyleStore:**\n\n"
                             "• **Tienda Online / Web:** Procesamos pagos seguros mediante **PayPal** (saldo PayPal y tarjetas internacionales Visa/MasterCard).\n"
                             "• **Caja Física / Tiendas:** Aceptamos **Efectivo** (con cálculo de vuelto) y **Código QR Simple** (transferencia bancaria inmediata).\n"
                             "• Puedes consultar todos tus recibos y notas en la sección Mis Pagos.",
                "chips": [
                    {"label": "💳 Ver Mis Pagos", "action": "navigate", "route": "/cuenta/mis-pagos"},
                    {"label": "🛍️ Ir al Carrito", "action": "navigate", "route": "/carrito"},
                ],
            }

        # 4. Envíos / Yango / Delivery / Tracking
        if any(w in norm for w in ["envio", "envios", "yango", "delivery", "ubicacion maps", "costo envio", "seguimiento"]):
            return {
                "respuesta": "🛵 **Envíos y Entregas con Yango Delivery:**\n\n"
                             "• Realizamos envíos a domicilio mediante moto/auto a través del servicio de **Yango**.\n"
                             "• Al finalizar tu pedido, debes proporcionar tu **enlace de Google Maps o Apple Maps** para que el conductor llegue a tu puerta con exactitud.\n"
                             "• La tarifa es variable según la app de Yango (distancia, clima, horario). Nuestro encargado te contactará o despachará tu orden inmediatamente.",
                "chips": [
                    {"label": "📦 Ver Estado de Pedidos", "action": "navigate", "route": "/cuenta/mis-compras"},
                    {"label": "🛍️ Ver Mi Carrito", "action": "navigate", "route": "/carrito"},
                ],
            }

        # 5. Reservas de Prendas
        if any(w in norm for w in ["reserva", "reservar", "apartar", "separar prenda"]):
            return {
                "respuesta": "🔖 **Políticas de Reserva de Prendas:**\n\n"
                             "• Para reservar una prenda sin costo inicial, debes contar con **al menos 1 compra previa pagada** en StyleStore.\n"
                             "• Las reservas tienen una vigencia máxima de **hasta 7 días calendario**.\n"
                             "• Debes seleccionar la sucursal física en la que pasarás a probarte y retirar la prenda.",
                "chips": [
                    {"label": "🔖 Mis Reservas", "action": "navigate", "route": "/reservas"},
                    {"label": "👗 Catálogo para Reservar", "action": "navigate", "route": "/catalogo"},
                ],
            }

        # 6. Cambios y Devoluciones
        if any(w in norm for w in ["cambio", "devolucion", "devolver", "cambiar prenda", "talla incorrecta", "garantia"]):
            return {
                "respuesta": "🔄 **Cambios y Devoluciones:**\n\n"
                             "• Puedes solicitar un cambio de talla, color o devolución dentro de los **7 días posteriores a tu compra**.\n"
                             "• La prenda debe encontrarse en perfectas condiciones y con etiquetas.\n"
                             "• Ve a **Mis Compras**, selecciona tu pedido y pulsa 'Solicitar Cambio / Devolución'. El encargado revisará tu caso para canjearlo en la sucursal que elijas.",
                "chips": [
                    {"label": "🔄 Solicitar Cambio en Mis Compras", "action": "navigate", "route": "/cuenta/mis-compras"},
                    {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                ],
            }

        # 7. Temporadas y Colecciones
        if any(w in norm for w in ["temporada", "coleccion", "colecciones", "verano", "invierno", "otono", "primavera"]):
            colecciones = self.db.query(Coleccion).filter(Coleccion.is_active == True).limit(5).all()
            temporadas = self.db.query(Temporada).filter(Temporada.is_active == True).limit(5).all()

            col_names = ", ".join([c.nombre for c in colecciones]) if colecciones else "Colección Actual"
            temp_names = ", ".join([t.nombre for t in temporadas]) if temporadas else "Temporada Actual"

            return {
                "respuesta": f"✨ **Moda y Tendencias StyleStore:**\n\n"
                             f"• **Colecciones Destacadas:** {col_names}\n"
                             f"• **Temporadas Disponibles:** {temp_names}\n\n"
                             f"Explora prendas exclusivas organizadas por estilo en nuestro catálogo interactivo.",
                "chips": [
                    {"label": "✨ Explorar Catálogo", "action": "navigate", "route": "/catalogo"},
                ],
            }

        # 8. Estado de mis pedidos / compras del usuario actual
        if any(w in norm for w in ["mi pedido", "mis compras", "mis pedidos", "estado de mi pedido", "mi orden", "donde esta mi compra"]):
            if not user:
                return {
                    "respuesta": "Para consultar el estado de tus compras, por favor inicia sesión con tu cuenta.",
                    "chips": [{"label": "Iniciar Sesión", "action": "navigate", "route": "/login"}],
                }

            cliente = self.db.query(Cliente).filter(Cliente.user_id == user.id).first()
            if not cliente:
                return {
                    "respuesta": "No encontramos un perfil de cliente asociado a tu cuenta. Puedes explorar el catálogo y realizar tu primera compra.",
                    "chips": [{"label": "👗 Catálogo", "action": "navigate", "route": "/catalogo"}],
                }

            ultimas_ventas = self.db.query(OrdenVenta).filter(
                OrdenVenta.cliente_id == cliente.id
            ).order_by(OrdenVenta.id.desc()).limit(3).all()

            if not ultimas_ventas:
                return {
                    "respuesta": f"Hola {user.name}, aún no tienes compras registradas en StyleStore. ¡Te invitamos a ver las novedades de la temporada!",
                    "chips": [{"label": "🛍️ Ir al Catálogo", "action": "navigate", "route": "/catalogo"}],
                }

            lineas = [f"📦 **Tus compras recientes, {user.name}:**\n"]
            for v in ultimas_ventas:
                ticket = v.ticket_numero or f"ORD-{v.id:04d}"
                lineas.append(f"• **{ticket}** | {v.fecha.strftime('%d/%m/%Y')} | Estado: **{v.estado.upper()}** | Total: Bs. {float(v.total):.2f}")

            return {
                "respuesta": "\n".join(lineas),
                "chips": [
                    {"label": "📦 Ver Todas Mis Compras", "action": "navigate", "route": "/cuenta/mis-compras"},
                    {"label": "💳 Ver Mis Recibos", "action": "navigate", "route": "/cuenta/mis-pagos"},
                ],
            }

        # 9. Búsqueda inteligente de productos / ropa
        # Palabras clave de categorías o tipos de prenda
        terminos = [t for t in norm.split() if len(t) > 3 and t not in ["para", "como", "quiero", "donde", "tiene", "tienen", "venden", "precio", "cuanto"]]
        if terminos:
            filtro_or = [Producto.nombre.ilike(f"%{t}%") for t in terminos]
            filtro_or.extend([Producto.descripcion.ilike(f"%{t}%") for t in terminos])
            productos = self.db.query(Producto).filter(or_(*filtro_or)).limit(4).all()

            if productos:
                lineas = ["👗 **Encontré estas prendas relacionadas con tu búsqueda:**\n"]
                for p in productos:
                    lineas.append(f"• **{p.nombre}** (Ref: {p.codigo}) - Bs. {float(p.precio):.2f}")
                lineas.append("\nPuedes ver detalles, tallas y colores disponibles en el catálogo.")
                return {
                    "respuesta": "\n".join(lineas),
                    "chips": [
                        {"label": "👗 Ver en Catálogo", "action": "navigate", "route": "/catalogo"},
                        {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                    ],
                }

        # 10. Respuesta por defecto
        return {
            "respuesta": "Entiendo tu consulta. Como asistente virtual de StyleStore puedo ayudarte a consultar sucursales, recomendaciones de ropa, pedidos, envíos con Yango, políticas de reserva o solicitar cambios. ¿Cuál de estas opciones te gustaría explorar?",
            "chips": [
                {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                {"label": "👗 Catálogo Online", "action": "navigate", "route": "/catalogo"},
                {"label": "📦 Mis Compras", "action": "navigate", "route": "/cuenta/mis-compras"},
                {"label": "🔄 Cambios y Devoluciones", "action": "navigate", "route": "/cuenta/mis-compras"},
            ],
        }
