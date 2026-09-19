"""
Reportes endpoints.
Exportación de datos de Ventas e Inventario a Excel (.xlsx) y PDF (.pdf).
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.report_service import ReportService
from app.services.bitacora_service import BitacoraService
from app.api.deps import get_current_user

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("/ventas/excel", summary="Exportar reporte de ventas en formato Excel")
async def export_ventas_excel(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    sucursal_id: Optional[int] = None,
    metodo_pago: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera y descarga el archivo Excel de ventas filtradas."""
    service = ReportService(db)
    buffer = service.generate_ventas_excel(fecha_inicio, fecha_fin, sucursal_id, metodo_pago)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Exportó reporte de ventas en formato Excel (.xlsx)",
        module="reportes",
    )

    filename = f"ventas_stylestore_{date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/ventas/pdf", summary="Exportar reporte de ventas en formato PDF")
async def export_ventas_pdf(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    sucursal_id: Optional[int] = None,
    metodo_pago: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera y descarga el archivo PDF de ventas."""
    service = ReportService(db)
    buffer = service.generate_ventas_pdf(fecha_inicio, fecha_fin, sucursal_id, metodo_pago)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Exportó reporte de ventas en formato PDF (.pdf)",
        module="reportes",
    )

    filename = f"ventas_stylestore_{date.today().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventario/excel", summary="Exportar reporte de inventario en Excel")
async def export_inventario_excel(
    sucursal_id: Optional[int] = None,
    solo_bajo_stock: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera y descarga el archivo Excel de inventario."""
    service = ReportService(db)
    buffer = service.generate_inventario_excel(sucursal_id, solo_bajo_stock)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Exportó reporte de inventario en Excel (.xlsx)",
        module="reportes",
    )

    filename = f"inventario_stylestore_{date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventario/pdf", summary="Exportar reporte de inventario en PDF")
async def export_inventario_pdf(
    sucursal_id: Optional[int] = None,
    solo_bajo_stock: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera y descarga el archivo PDF de inventario."""
    service = ReportService(db)
    buffer = service.generate_inventario_pdf(sucursal_id, solo_bajo_stock)

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Exportó reporte de inventario en PDF (.pdf)",
        module="reportes",
    )

    filename = f"inventario_stylestore_{date.today().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/ventas/preview", summary="Previsualizar reporte de ventas en JSON")
async def preview_ventas(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    sucursal_id: Optional[int] = None,
    metodo_pago: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna los datos estructurados en JSON para la previsualización interactiva de ventas."""
    service = ReportService(db)
    ventas = service.get_ventas_data(fecha_inicio, fecha_fin, sucursal_id, metodo_pago)
    total_monto = sum(float(v.total) for v in ventas)
    from app.services.report_service import _get_cliente_nombre, _get_cliente_email, _get_sucursal_nombre
    items = []
    for v in ventas:
        items.append({
            "id": v.id,
            "ticket_numero": v.ticket_numero or f"ORD-{v.id:04d}",
            "fecha": v.fecha.strftime("%d/%m/%Y") if v.fecha else "",
            "cliente_nombre": _get_cliente_nombre(v.cliente),
            "cliente_email": _get_cliente_email(v.cliente),
            "codigo_cliente": v.codigo_cliente,
            "sucursal_nombre": _get_sucursal_nombre(v.sucursal),
            "metodo_pago": (v.metodo_pago or "EFECTIVO").upper(),
            "estado": v.estado.capitalize() if v.estado else "Pendiente",
            "total": float(v.total),
            "articulos_count": len(v.detalles) if v.detalles else 0,
        })
    return {
        "total_registros": len(items),
        "total_monto": total_monto,
        "items": items,
    }


@router.get("/inventario/preview", summary="Previsualizar reporte de inventario en JSON")
async def preview_inventario(
    sucursal_id: Optional[int] = None,
    solo_bajo_stock: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna los datos estructurados en JSON para la previsualización interactiva de inventario."""
    service = ReportService(db)
    items_raw = service.get_inventario_data(sucursal_id, solo_bajo_stock)
    from app.services.report_service import _get_sucursal_nombre
    items = []
    criticos_count = 0
    for it in items_raw:
        pc = it.producto_color
        prod = pc.producto if pc else None
        color_nom = pc.color.nombre if (pc and pc.color) else "-"
        talla_nom = it.talla.nombre if it.talla else "-"
        es_critico = it.cantidad <= 5
        if es_critico:
            criticos_count += 1
        items.append({
            "id": it.id,
            "codigo": prod.codigo if prod else "-",
            "producto_nombre": prod.nombre if prod else "-",
            "color_nombre": color_nom,
            "talla_nombre": talla_nom,
            "sucursal_nombre": _get_sucursal_nombre(it.sucursal),
            "cantidad": it.cantidad,
            "es_critico": es_critico,
        })
    return {
        "total_registros": len(items),
        "total_criticos": criticos_count,
        "items": items,
    }
