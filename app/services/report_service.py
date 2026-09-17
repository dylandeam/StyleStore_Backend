"""
Servicio de Reportes Dinámicos StyleStore.
Genera reportes de Ventas, Inventario y Clientes en Excel (.xlsx con openpyxl) y PDF (.pdf con reportlab).
"""
import io
import re
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.models.orden_venta import OrdenVenta, DetalleVenta
from app.models.producto import Producto
from app.models.producto_color import ProductoColor
from app.models.color import Color
from app.models.talla import Talla
from app.models.stock_inventario import StockInventario
from app.models.sucursal import Sucursal
from app.models.cliente import Cliente
from app.models.user import User


def clean_sheet_title(title: str) -> str:
    """Sanitiza títulos de hojas de Excel: max 31 chars, sin caracteres prohibidos."""
    sanitized = re.sub(r'[\\/*?:\[\]]', '', title)
    return sanitized[:31] if sanitized else "Reporte"


class ReportService:
    """Generador de reportes en Excel y PDF con estética StyleStore."""

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # 1. REPORTES DE VENTAS
    # ==========================================

    def get_ventas_data(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        sucursal_id: Optional[int] = None,
        metodo_pago: Optional[str] = None,
    ) -> List[OrdenVenta]:
        """Obtiene las ventas filtradas."""
        query = self.db.query(OrdenVenta).options(
            joinedload(OrdenVenta.cliente),
            joinedload(OrdenVenta.sucursal),
            joinedload(OrdenVenta.detalles),
        )
        if fecha_inicio:
            query = query.filter(OrdenVenta.fecha >= fecha_inicio)
        if fecha_fin:
            query = query.filter(OrdenVenta.fecha <= fecha_fin)
        if sucursal_id:
            query = query.filter(OrdenVenta.sucursal_id == sucursal_id)
        if metodo_pago:
            query = query.filter(OrdenVenta.metodo_pago == metodo_pago)

        return query.order_by(OrdenVenta.fecha.desc(), OrdenVenta.id.desc()).all()

    def generate_ventas_excel(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        sucursal_id: Optional[int] = None,
        metodo_pago: Optional[str] = None,
    ) -> io.BytesIO:
        """Genera un archivo Excel con el reporte de ventas."""
        ventas = self.get_ventas_data(fecha_inicio, fecha_fin, sucursal_id, metodo_pago)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = clean_sheet_title("Ventas StyleStore")

        # Paleta de colores
        navy_fill = PatternFill(start_color="14263D", end_color="14263D", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Arial", size=16, bold=True, color="14263D")
        bold_font = Font(name="Arial", size=10, bold=True)
        normal_font = Font(name="Arial", size=10)
        thin_border = Border(
            left=Side(style='thin', color='E0E0E0'),
            right=Side(style='thin', color='E0E0E0'),
            top=Side(style='thin', color='E0E0E0'),
            bottom=Side(style='thin', color='E0E0E0')
        )

        # Encabezado del reporte
        ws.merge_cells("A1:G1")
        ws["A1"] = "StyleStore - Reporte Detallado de Ventas"
        ws["A1"].font = title_font
        ws["A1"].alignment = Alignment(horizontal="left", vertical="center")

        gen_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws["A2"] = f"Generado: {gen_date} | Total Registros: {len(ventas)}"
        ws["A2"].font = Font(name="Arial", size=9, italic=True, color="666666")

        # Columnas
        headers = ["N° Venta / Ticket", "Fecha", "Cliente", "Sucursal", "Método Pago", "Estado", "Total ($)"]
        ws.row_dimensions[4].height = 24

        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_idx, value=header)
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Filas de datos
        row_idx = 5
        gran_total = Decimal("0.00")

        for v in ventas:
            total_num = float(v.total)
            gran_total += Decimal(str(v.total))
            ws.cell(row=row_idx, column=1, value=v.ticket_numero or f"ORD-{v.id:04d}").font = normal_font
            ws.cell(row=row_idx, column=2, value=v.fecha.strftime("%Y-%m-%d") if v.fecha else "").font = normal_font
            ws.cell(row=row_idx, column=3, value=v.cliente.nombre if v.cliente else "Cliente General").font = normal_font
            ws.cell(row=row_idx, column=4, value=v.sucursal.nombre if v.sucursal else "Central").font = normal_font
            ws.cell(row=row_idx, column=5, value=(v.metodo_pago or "efectivo").upper()).font = normal_font
            ws.cell(row=row_idx, column=6, value=v.estado.capitalize()).font = normal_font
            
            c_total = ws.cell(row=row_idx, column=7, value=total_num)
            c_total.font = normal_font
            c_total.number_format = '$#,##0.00'
            c_total.alignment = Alignment(horizontal="right")

            for c in range(1, 8):
                ws.cell(row=row_idx, column=c).border = thin_border
            row_idx += 1

        # Fila de Total
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)
        tot_label = ws.cell(row=row_idx, column=1, value="TOTAL GENERAL:")
        tot_label.font = bold_font
        tot_label.alignment = Alignment(horizontal="right", vertical="center")
        
        tot_val = ws.cell(row=row_idx, column=7, value=float(gran_total))
        tot_val.font = bold_font
        tot_val.number_format = '$#,##0.00'
        tot_val.alignment = Alignment(horizontal="right", vertical="center")

        # Auto-ajuste de anchos de columna
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def generate_ventas_pdf(
        self,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        sucursal_id: Optional[int] = None,
        metodo_pago: Optional[str] = None,
    ) -> io.BytesIO:
        """Genera un archivo PDF con el reporte de ventas."""
        ventas = self.get_ventas_data(fecha_inicio, fecha_fin, sucursal_id, metodo_pago)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#14263D')
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#666666')
        )

        elements = []
        elements.append(Paragraph("StyleStore - Reporte de Ventas", title_style))
        gen_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        elements.append(Paragraph(f"Emitido el: {gen_str} | Ventas listadas: {len(ventas)}", subtitle_style))
        elements.append(Spacer(1, 15))

        # Tabla de ventas
        table_data = [["N° Ticket", "Fecha", "Cliente", "Sucursal", "Método", "Total"]]
        gran_total = Decimal("0.00")

        for v in ventas:
            gran_total += Decimal(str(v.total))
            table_data.append([
                v.ticket_numero or f"ORD-{v.id:04d}",
                v.fecha.strftime("%d/%m/%Y") if v.fecha else "",
                (v.cliente.nombre if v.cliente else "Cliente General")[:20],
                (v.sucursal.nombre if v.sucursal else "Central")[:16],
                (v.metodo_pago or "efectivo")[:10].upper(),
                f"${float(v.total):.2f}"
            ])

        table_data.append(["", "", "", "", "TOTAL:", f"${float(gran_total):.2f}"])

        col_widths = [80, 70, 140, 110, 70, 70]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14263D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#F8F9FA'), colors.white]),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor('#14263D')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # ==========================================
    # 2. REPORTES DE INVENTARIO Y STOCK CRÍTICO
    # ==========================================

    def get_inventario_data(self, sucursal_id: Optional[int] = None, solo_bajo_stock: bool = False):
        """Obtiene el stock actual agrupado con producto, color, talla y sucursal."""
        query = self.db.query(StockInventario).options(
            joinedload(StockInventario.sucursal),
            joinedload(StockInventario.talla),
            joinedload(StockInventario.producto_color).joinedload(ProductoColor.producto),
            joinedload(StockInventario.producto_color).joinedload(ProductoColor.color),
        )
        if sucursal_id:
            query = query.filter(StockInventario.sucursal_id == sucursal_id)
        if solo_bajo_stock:
            query = query.filter(StockInventario.cantidad <= 5)

        return query.all()

    def generate_inventario_excel(self, sucursal_id: Optional[int] = None, solo_bajo_stock: bool = False) -> io.BytesIO:
        """Genera un archivo Excel con el reporte de inventario."""
        items = self.get_inventario_data(sucursal_id, solo_bajo_stock)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = clean_sheet_title("Inventario StyleStore")

        navy_fill = PatternFill(start_color="14263D", end_color="14263D", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Arial", size=16, bold=True, color="14263D")
        normal_font = Font(name="Arial", size=10)
        thin_border = Border(
            left=Side(style='thin', color='E0E0E0'),
            right=Side(style='thin', color='E0E0E0'),
            top=Side(style='thin', color='E0E0E0'),
            bottom=Side(style='thin', color='E0E0E0')
        )

        ws.merge_cells("A1:F1")
        ws["A1"] = "StyleStore - Reporte de Inventario y Stock"
        ws["A1"].font = title_font

        ws["A2"] = f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Total Registros: {len(items)}"
        ws["A2"].font = Font(name="Arial", size=9, italic=True, color="666666")

        headers = ["Código", "Producto", "Color", "Talla", "Sucursal", "Stock Actual"]
        ws.row_dimensions[4].height = 24
        for col_idx, h in enumerate(headers, 1):
            c = ws.cell(row=4, column=col_idx, value=h)
            c.fill = navy_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")

        row_idx = 5
        for item in items:
            p_color = item.producto_color
            prod = p_color.producto if p_color else None
            color_nom = p_color.color.nombre if (p_color and p_color.color) else "-"
            talla_nom = item.talla.nombre if item.talla else "-"

            ws.cell(row=row_idx, column=1, value=prod.codigo if prod else "-").font = normal_font
            ws.cell(row=row_idx, column=2, value=prod.nombre if prod else "-").font = normal_font
            ws.cell(row=row_idx, column=3, value=color_nom).font = normal_font
            ws.cell(row=row_idx, column=4, value=talla_nom).font = normal_font
            ws.cell(row=row_idx, column=5, value=item.sucursal.nombre if item.sucursal else "Central").font = normal_font
            
            c_stock = ws.cell(row=row_idx, column=6, value=item.cantidad)
            c_stock.font = normal_font
            c_stock.alignment = Alignment(horizontal="right")
            if item.cantidad <= 3:
                c_stock.fill = PatternFill(start_color="FFE0E0", end_color="FFE0E0", fill_type="solid")

            for c in range(1, 7):
                ws.cell(row=row_idx, column=c).border = thin_border
            row_idx += 1

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def generate_inventario_pdf(self, sucursal_id: Optional[int] = None, solo_bajo_stock: bool = False) -> io.BytesIO:
        """Genera un archivo PDF con el inventario."""
        items = self.get_inventario_data(sucursal_id, solo_bajo_stock)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('InvTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#14263D'))
        elements = [
            Paragraph("StyleStore - Reporte de Inventario", title_style),
            Spacer(1, 15)
        ]

        table_data = [["Código", "Producto", "Color", "Talla", "Sucursal", "Stock"]]
        for it in items:
            pc = it.producto_color
            prod = pc.producto if pc else None
            table_data.append([
                prod.codigo if prod else "-",
                (prod.nombre if prod else "-")[:25],
                pc.color.nombre[:10] if (pc and pc.color) else "-",
                it.talla.nombre[:6] if it.talla else "-",
                (it.sucursal.nombre if it.sucursal else "Central")[:15],
                str(it.cantidad)
            ])

        col_widths = [70, 180, 70, 50, 100, 60]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14263D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8F9FA'), colors.white]),
        ]))
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer
