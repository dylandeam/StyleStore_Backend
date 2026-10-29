"""Branded, tenant-scoped PDF catalog export."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from base64 import b64decode
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.producto_talla_precio import ProductoTallaPrecio
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.promocion_service import PromocionService
from app.services.tenant_scope import effective_empresa_id


class CatalogPdfService:
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.current_user = current_user

    def generate(
        self,
        *,
        categoria_id: int | None = None,
        temporada_id: int | None = None,
        coleccion_id: int | None = None,
        sucursal_id: int | None = None,
        search: str | None = None,
    ) -> tuple[bytes, str]:
        empresa_id = effective_empresa_id(self.current_user)
        if empresa_id is None:
            raise ValueError("Selecciona un tenant antes de exportar el catálogo.")
        empresa = self.db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            raise ValueError("El tenant seleccionado no existe.")

        query = self.db.query(Producto).filter(
            Producto.empresa_id == empresa_id,
            Producto.active.is_(True),
            Producto.visible_en_catalogo.is_(True),
        )
        if categoria_id:
            query = query.filter(Producto.categoria_id == categoria_id)
        if temporada_id:
            query = query.filter(Producto.temporada_id == temporada_id)
        if coleccion_id:
            query = query.filter(Producto.coleccion_id == coleccion_id)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(or_(Producto.nombre.ilike(term), Producto.descripcion.ilike(term)))
        products = query.order_by(Producto.nombre.asc()).all()

        branch = None
        if sucursal_id:
            branch = self.db.query(Sucursal).filter(
                Sucursal.id == sucursal_id,
                Sucursal.empresa_id == empresa_id,
            ).first()
            if not branch:
                raise ValueError("La sucursal no pertenece al tenant seleccionado.")

        output = BytesIO()
        primary = self._color(empresa.color_primario, "#14263D")
        accent = self._color(empresa.color_acento, "#274C77")
        surface = self._color(empresa.color_secundario, "#FBF8F1")
        text_color = self._color(empresa.color_texto, "#172536")
        primary_text = self._contrast_color(primary)
        brand = empresa.nombre_marca or empresa.nombre

        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=15 * mm,
            bottomMargin=16 * mm,
            title=f"Catálogo {brand}",
            author=brand,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CatalogTitle", parent=styles["Title"], fontName="Helvetica-Bold",
            fontSize=22, leading=26, textColor=primary, spaceAfter=3 * mm,
        )
        brand_title_style = ParagraphStyle(
            "BrandTitle", parent=title_style, textColor=primary_text,
            alignment=TA_LEFT, spaceAfter=1.5 * mm,
        )
        subtitle_style = ParagraphStyle(
            "CatalogSubtitle", parent=styles["BodyText"], fontSize=9.5,
            leading=13, textColor=accent,
        )
        brand_subtitle_style = ParagraphStyle(
            "BrandSubtitle", parent=subtitle_style, textColor=primary_text,
            alignment=TA_LEFT,
        )
        name_style = ParagraphStyle(
            "ProductName", parent=styles["Heading3"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=primary, spaceAfter=1.5 * mm,
        )
        body_style = ParagraphStyle(
            "ProductBody", parent=styles["BodyText"], fontSize=8.5,
            leading=11.5, textColor=text_color,
        )
        price_style = ParagraphStyle(
            "ProductPrice", parent=styles["Heading2"], fontName="Helvetica-Bold",
            fontSize=14, leading=17, textColor=accent, alignment=TA_RIGHT,
        )
        story = []

        logo = self._image_flowable(empresa.logo_url, 25 * mm, 25 * mm)
        brand_copy = [Paragraph(escape(brand), brand_title_style)]
        if empresa.eslogan:
            brand_copy.append(Paragraph(escape(empresa.eslogan), brand_subtitle_style))
        header = Table(
            [[logo or "", brand_copy]],
            colWidths=[31 * mm, 144 * mm],
            hAlign="LEFT",
        )
        header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), primary),
            ("BOX", (0, 0), (-1, -1), 1, primary),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]))
        story.extend([header, Spacer(1, 6 * mm)])

        scope_parts = ["Catálogo completo" if not any((categoria_id, temporada_id, coleccion_id, search)) else "Selección personalizada"]
        if branch:
            scope_parts.append(f"Sucursal: {branch.nombre}")
        if search:
            scope_parts.append(f"Búsqueda: {search.strip()}")
        story.append(Paragraph(" · ".join(escape(part) for part in scope_parts), subtitle_style))
        story.append(Paragraph(f"{len(products)} prenda(s) disponibles", body_style))
        story.extend([Spacer(1, 2 * mm), HRFlowable(width="100%", color=accent, thickness=1), Spacer(1, 4 * mm)])

        if not products:
            story.append(Paragraph("No hay prendas que coincidan con los filtros seleccionados.", body_style))

        for product in products:
            stock_query = self.db.query(func.coalesce(func.sum(StockInventario.cantidad), 0)).join(
                ProductoColor, StockInventario.producto_color_id == ProductoColor.id
            ) if product.colores_rel else None
            stock_total = 0
            if stock_query is not None:
                stock_query = stock_query.filter(ProductoColor.producto_codigo == product.codigo)
                if branch:
                    stock_query = stock_query.filter(StockInventario.sucursal_id == branch.id)
                stock_total = int(stock_query.scalar() or 0)
            if branch and stock_total <= 0:
                continue

            pct = PromocionService(self.db).porcentaje_producto(product)
            final_price = float(product.precio) * (100 - pct) / 100
            tags = [product.categoria.nombre if product.categoria else "Prenda"]
            if product.temporada:
                tags.append(product.temporada.nombre)
            if product.coleccion:
                tags.append(product.coleccion.nombre)
            details = [
                Paragraph(escape(product.nombre), name_style),
                Paragraph(f"Ref. {escape(product.codigo)} · {escape(' · '.join(tags))}", subtitle_style),
            ]
            if product.descripcion:
                details.append(Spacer(1, 1.5 * mm))
                details.append(Paragraph(escape(product.descripcion[:260]), body_style))
            color_names = sorted({
                rel.color.nombre for rel in product.colores_rel if rel.color and rel.color.nombre
            })
            details.append(Spacer(1, 2 * mm))
            details.append(Paragraph(
                f"<b>Color(es):</b> {escape(', '.join(color_names) if color_names else 'No especificado')}",
                body_style,
            ))
            details.append(Paragraph(f"<b>Existencias:</b> {stock_total}", body_style))

            size_rows = self._size_price_rows(product, branch, pct)
            if size_rows:
                size_header = [
                    Paragraph("Talla", body_style),
                    Paragraph("Precio", body_style),
                    Paragraph("Stock", body_style),
                ]
                size_table = Table(
                    [size_header] + [
                        [
                            Paragraph(escape(row[0]), body_style),
                            Paragraph(f"Bs. {row[1]:.2f}", body_style),
                            Paragraph(str(row[2]), body_style),
                        ]
                        for row in size_rows
                    ],
                    # Prioriza la talla para conservar nombres comerciales completos
                    # (por ejemplo, "XXL AURORA") en una sola línea legible.
                    colWidths=[30 * mm, 23 * mm, 13 * mm],
                    hAlign="LEFT",
                )
                size_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), surface),
                    ("TEXTCOLOR", (0, 0), (-1, -1), text_color),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D9D0BF")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                details.extend([Spacer(1, 2 * mm), Paragraph("Tallas y precios", name_style), size_table])

            price_text = f"Bs. {final_price:.2f}"
            if pct:
                price_text += f"<br/><font size='8'>Antes Bs. {float(product.precio):.2f} · {pct}% OFF</font>"
            card = Table(
                [[self._image_flowable(product.foto, 34 * mm, 34 * mm) or "", details, Paragraph(price_text, price_style)]],
                colWidths=[39 * mm, 102 * mm, 34 * mm],
            )
            card.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), .65, colors.HexColor("#D9D0BF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.extend([KeepTogether(card), Spacer(1, 3 * mm)])

        def footer(canvas, doc):
            canvas.saveState()
            if doc.page > 1:
                canvas.setFillColor(surface)
                canvas.roundRect(16 * mm, 278 * mm, 178 * mm, 10 * mm, 2 * mm, fill=1, stroke=0)
                canvas.setFillColor(primary)
                canvas.setFont("Helvetica-Bold", 10)
                canvas.drawString(20 * mm, 282 * mm, brand)
                canvas.setFont("Helvetica", 8)
                canvas.drawRightString(190 * mm, 282 * mm, "Catálogo · continuación")
            canvas.setStrokeColor(accent)
            canvas.line(16 * mm, 12 * mm, 194 * mm, 12 * mm)
            canvas.setFillColor(text_color)
            canvas.setFont("Helvetica", 7.5)
            canvas.drawString(16 * mm, 8 * mm, f"{brand} · Catálogo generado desde StyleStore")
            canvas.drawRightString(194 * mm, 8 * mm, f"Página {doc.page}")
            canvas.restoreState()

        document.build(story, onFirstPage=footer, onLaterPages=footer)
        filename = f"catalogo-{empresa.codigo}.pdf"
        return output.getvalue(), filename

    def _size_price_rows(
        self, product: Producto, branch: Sucursal | None, discount_pct: int
    ) -> list[tuple[str, float, int]]:
        """Resume cada talla con su precio efectivo y stock en el ámbito exportado."""
        configured = {
            item.talla_id: float(item.precio) for item in product.precios_talla_rel
        }
        inventory = []
        for color_rel in product.colores_rel:
            for stock in color_rel.inventarios_rel:
                if branch and stock.sucursal_id != branch.id:
                    continue
                inventory.append(stock)
        size_ids = set(configured) | {stock.talla_id for stock in inventory}
        rows: list[tuple[str, float, int]] = []
        for size_id in size_ids:
            size_stocks = [stock for stock in inventory if stock.talla_id == size_id]
            size = next((stock.talla for stock in size_stocks if stock.talla), None)
            if size is None:
                configured_row = self.db.query(ProductoTallaPrecio).filter(
                    ProductoTallaPrecio.producto_codigo == product.codigo,
                    ProductoTallaPrecio.talla_id == size_id,
                ).first()
                size = configured_row.talla if configured_row else None
            variant_prices = [float(stock.precio_variante) for stock in size_stocks if stock.precio_variante is not None]
            base_price = configured.get(size_id) or (variant_prices[0] if variant_prices else float(product.precio))
            effective_price = base_price * (100 - discount_pct) / 100
            rows.append((size.nombre if size else f"#{size_id}", effective_price, sum(stock.cantidad for stock in size_stocks)))
        return sorted(rows, key=lambda item: item[0])

    def _image_flowable(self, raw_path: str | None, max_width: float, max_height: float):
        content = self._image_bytes(raw_path)
        if not content:
            return None
        try:
            image = Image(BytesIO(content))
            ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
            image.drawWidth = image.imageWidth * ratio
            image.drawHeight = image.imageHeight * ratio
            return image
        except Exception:
            return None

    def _image_bytes(self, raw_path: str | None) -> bytes | None:
        if not raw_path:
            return None
        if raw_path.startswith("data:"):
            try:
                return b64decode(raw_path.split(",", 1)[1])
            except (ValueError, IndexError):
                return None
        if raw_path.startswith(("http://", "https://")):
            raw_path = urlparse(raw_path).path
        normalized = raw_path.replace("\\", "/").lstrip("/")
        parts = normalized.split("/")
        if len(parts) >= 2:
            record = self.db.query(UploadedFile).filter(
                UploadedFile.folder == parts[-2],
                UploadedFile.filename == parts[-1],
                UploadedFile.empresa_id == effective_empresa_id(self.current_user),
            ).first()
            if record:
                return record.data
        local = Path.cwd() / normalized
        try:
            if local.is_file() and (Path.cwd() / "uploads") in local.resolve().parents:
                return local.read_bytes()
        except OSError:
            return None
        return None

    @staticmethod
    def _color(value: str | None, fallback: str):
        try:
            return colors.HexColor(value or fallback)
        except ValueError:
            return colors.HexColor(fallback)

    @staticmethod
    def _contrast_color(background):
        red, green, blue = background.red, background.green, background.blue
        def linear(channel: float) -> float:
            return channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
        luminance = .2126 * linear(red) + .7152 * linear(green) + .0722 * linear(blue)
        return colors.white if luminance < .42 else colors.HexColor("#172536")
