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
