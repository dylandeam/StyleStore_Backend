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
    """Normaliza texto eliminando signos de puntuación, tildes y pasando a minúsculas."""
    text = re.sub(r"[^\w\s]", " ", text.lower().strip())
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def _stem_palabra(palabra: str) -> str:
    """Obtiene la raíz léxica en español para singularizar plurales comunes (pantalones -> pantalon, camisas -> camisa)."""
    p = palabra.strip()
    if p.endswith("ces") and len(p) > 4:
        return p[:-3] + "z"
    if p.endswith("es") and len(p) > 4:
        return p[:-2]
    if p.endswith("s") and len(p) > 3 and not p.endswith("is"):
        return p[:-1]
    return p


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
                "respuesta": f"¡Hola{nombre}! 👋 Bienvenido a StyleStore. ¿En qué puedo colaborarte hoy? Puedes consultarme sobre nuestras sucursales, prendas disponibles, temporadas, estado de tus pedidos o decirme 'agrega el vestido rojo al carrito' para comprar directamente.",
                "chips": [
                    {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                    {"label": "👗 Catálogo de Ropa", "action": "navigate", "route": "/catalogo"},
                    {"label": "📦 Mis Compras", "action": "navigate", "route": "/cuenta/mis-compras"},
                    {"label": "💳 Métodos de Pago", "action": "navigate", "route": "/cuenta/mis-pagos"},
                ],
            }

        # 1.1 Acción Ejecutable: Agregar prenda al carrito (Punto 8 / v7)
        if any(f in norm for f in ["agrega", "agregar", "anade", "anadir", "pon en mi bolsa", "pon al carrito", "comprar", "metelo"]):
            cant_match = re.search(r"\b(\d+)\b", norm)
            cantidad = int(cant_match.group(1)) if cant_match else 1
            if cantidad < 1:
                cantidad = 1

            prods = self.db.query(Producto).filter(Producto.active == True).all()
            matched_prod = None
            for p in prods:
                p_norm = _normalize(p.nombre)
                # Coincidencia directa o parcial
                if p_norm in norm or any(w in norm for w in p_norm.split() if len(w) >= 4):
                    matched_prod = p
                    break

            if matched_prod:
                from app.models.producto_color import ProductoColor
                from app.models.stock_inventario import StockInventario
                pc = self.db.query(ProductoColor).filter(ProductoColor.producto_codigo == matched_prod.codigo).first()
                color_id = pc.color_id if pc else 1
                color_nom = pc.color.nombre if (pc and pc.color) else "Estándar"

                stk = None
                if pc:
                    stk = self.db.query(StockInventario).filter(
                        StockInventario.producto_color_id == pc.id,
                        StockInventario.cantidad > 0
                    ).first()
                talla_id = stk.talla_id if stk else 1
                talla_nom = stk.talla.nombre if (stk and stk.talla) else "Única"

                return {
                    "respuesta": f"🛒 ¡Excelente elección! He añadido **{cantidad}x {matched_prod.nombre}** ({color_nom}, Talla {talla_nom}) directamente a tu bolsa de compras.",
                    "accion_ejecutable": {
                        "tipo": "add_to_cart",
                        "producto_codigo": matched_prod.codigo,
                        "producto_nombre": matched_prod.nombre,
                        "precio": float(matched_prod.precio),
                        "color_id": color_id,
                        "color_nombre": color_nom,
                        "talla_id": talla_id,
                        "talla_nombre": talla_nom,
                        "cantidad": cantidad,
                    },
                    "chips": [
                        {"label": "🛍️ Ir al Carrito a Pagar", "action": "navigate", "route": "/carrito"},
                        {"label": "👗 Ver Catálogo", "action": "navigate", "route": "/catalogo"},
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

        # 4. Envíos / Delivery StyleStore / Tracking
        if any(w in norm for w in ["envio", "envios", "delivery", "ubicacion maps", "costo envio", "seguimiento", "yango"]):
            return {
                "respuesta": "🛵 **Delivery StyleStore Oficial:**\n\n"
                             "• Realizamos despachos a domicilio mediante nuestro servicio propio de **Delivery StyleStore** con repartidores asignados.\n"
                             "• Al finalizar tu pedido, debes proporcionar tu **enlace de Google Maps o Apple Maps** para que el conductor llegue a tu puerta con exactitud.\n"
                             "• Podrás realizar seguimiento en tiempo real de tu pedido y consultar su estado en todo momento.",
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
            colecciones = self.db.query(Coleccion).filter(Coleccion.active == True).limit(5).all()
            temporadas = self.db.query(Temporada).limit(5).all()

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
                OrdenVenta.codigo_cliente == cliente.codigo
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

        # 9. Consulta general de ropa / catálogo ("que ropa tienen", "que prendas hay", etc.)
        if any(f in norm for f in ["que ropa", "que prendas", "que tienen", "que venden", "ver ropa", "mostrar ropa", "que hay"]):
            prods = self.db.query(Producto).filter(Producto.active == True).limit(5).all()
            if prods:
                lineas = ["👗 **¡En StyleStore contamos con variadas prendas de moda y temporada!**\n\nAlgunas de nuestras prendas destacadas son:\n"]
                for p in prods:
                    lineas.append(f"• **{p.nombre}** (Ref: {p.codigo}) - Bs. {float(p.precio):.2f}")
                lineas.append("\nPuedes explorar colores, tallas y stock en nuestro catálogo.")
                return {
                    "respuesta": "\n".join(lineas),
                    "chips": [
                        {"label": "👗 Ver Catálogo Completo", "action": "navigate", "route": "/catalogo"},
                        {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                    ],
                }

        # 10. Búsqueda inteligente de prendas / productos específicos (pantalones, camisas, vestidos, etc.)
        stopwords = {
            "para", "como", "quiero", "donde", "tiene", "tienen", "venden", "precio", "cuanto",
            "hay", "algun", "alguna", "algunos", "algunas", "ropa", "prenda", "prendas", "estilo",
            "tienda", "disponible", "disponibles", "favor", "buenas", "hola", "saber", "si"
        }
        palabras = [w for w in norm.split() if len(w) >= 3 and w not in stopwords]

        if palabras:
            terminos_busqueda = set()
            for w in palabras:
                terminos_busqueda.add(w)
                stem = _stem_palabra(w)
                if len(stem) >= 3:
                    terminos_busqueda.add(stem)

            filtro_or = []
            for t in terminos_busqueda:
                filtro_or.append(Producto.nombre.ilike(f"%{t}%"))
                filtro_or.append(Producto.descripcion.ilike(f"%{t}%"))

            productos = self.db.query(Producto).filter(or_(*filtro_or)).limit(4).all()

            if productos:
                lineas = ["👗 **¡Sí! Tenemos disponibles prendas que coinciden con tu búsqueda:**\n"]
                for p in productos:
                    lineas.append(f"• **{p.nombre}** (Ref: {p.codigo}) - Bs. {float(p.precio):.2f}")
                lineas.append("\nPuedes consultar colores, tallas y existencias en vivo en nuestro catálogo interactivo.")
                return {
                    "respuesta": "\n".join(lineas),
                    "chips": [
                        {"label": "👗 Ver en Catálogo", "action": "navigate", "route": "/catalogo"},
                        {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                        {"label": "🛍️ Ir al Carrito", "action": "navigate", "route": "/carrito"},
                    ],
                }
            else:
                prenda_buscada = palabras[0]
                return {
                    "respuesta": f"Por el momento no encontré prendas que coincidan exactamente con '{prenda_buscada}' en nuestro catálogo activo. Sin embargo, disponemos de camisas, pantalones, polos y novedades de temporada. ¡Te invitamos a ver todo el catálogo!",
                    "chips": [
                        {"label": "👗 Explorar Catálogo", "action": "navigate", "route": "/catalogo"},
                        {"label": "📍 Consultar Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                    ],
                }

        # 11. Respuesta por defecto
        return {
            "respuesta": "Entiendo tu consulta. Como asistente virtual de StyleStore puedo ayudarte a consultar sucursales, recomendaciones de ropa, pedidos, envíos con Delivery StyleStore, políticas de reserva o solicitar cambios. ¿Cuál de estas opciones te gustaría explorar?",
            "chips": [
                {"label": "📍 Ver Sucursales", "action": "navigate", "route": "/admin/sucursales"},
                {"label": "👗 Catálogo Online", "action": "navigate", "route": "/catalogo"},
                {"label": "📦 Mis Compras", "action": "navigate", "route": "/cuenta/mis-compras"},
                {"label": "🔄 Cambios y Devoluciones", "action": "navigate", "route": "/cuenta/mis-compras"},
            ],
        }
