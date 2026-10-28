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
from app.services.tenant_scope import get_scoped_sucursal
from app.api.deps import get_current_user, require_plan_capability

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
    dependencies=[Depends(require_plan_capability("reportes"))],
)


def _validate_report_sucursal(db: Session, current_user: User, sucursal_id: Optional[int]) -> None:
    """Valida que la sucursal pertenezca al tenant del usuario autenticado (REQ-063)."""
    if sucursal_id is not None and sucursal_id > 0:
        get_scoped_sucursal(db, current_user, sucursal_id)


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
    _validate_report_sucursal(db, current_user, sucursal_id)
    service = ReportService(db, current_user)
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
    _validate_report_sucursal(db, current_user, sucursal_id)
    service = ReportService(db, current_user)
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
    _validate_report_sucursal(db, current_user, sucursal_id)
    service = ReportService(db, current_user)
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
    _validate_report_sucursal(db, current_user, sucursal_id)
    service = ReportService(db, current_user)
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
    _validate_report_sucursal(db, current_user, sucursal_id)
    service = ReportService(db, current_user)
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
    _validate_report_sucursal(db, current_user, sucursal_id)
    service = ReportService(db, current_user)
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



# ==========================================
# DASHBOARD STATS (PUNTO 1)
# ==========================================

@router.get("/dashboard-stats", summary="Métricas estadísticas operativas del Dashboard")
async def get_dashboard_stats(
    sucursal_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.dashboard_service import DashboardService
    from app.models.empleado import Empleado

    if current_user.role in ["encargado", "vendedor"] and sucursal_id is None:
        emp = db.query(Empleado).filter(Empleado.user_id == current_user.id).first()
        if emp:
            sucursal_id = emp.sucursal_id

    if sucursal_id == 0:
        sucursal_id = None

    _validate_report_sucursal(db, current_user, sucursal_id)
    service = DashboardService(db, current_user)
    return service.get_dashboard_stats(sucursal_id=sucursal_id)


@router.get("/predicciones", summary="Pronóstico de ventas y segmentación ML por tenant")
async def get_ml_predictions(
    sucursal_id: Optional[int] = None,
    current_user: User = Depends(require_plan_capability("predicciones")),
    db: Session = Depends(get_db),
):
    from app.services.ml_service import MLService

    if sucursal_id == 0:
        sucursal_id = None
    _validate_report_sucursal(db, current_user, sucursal_id)
    return MLService(db, current_user).insights(sucursal_id=sucursal_id)


@router.get("/alertas-stock-predictivo", summary="Alertas predictivas de agotamiento de stock por variante (REQ-068)")
async def get_predictive_stock_alerts(
    sucursal_id: Optional[int] = None,
    criticidad: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ml_service import MLService

    if sucursal_id == 0:
        sucursal_id = None
    _validate_report_sucursal(db, current_user, sucursal_id)
    return MLService(db, current_user).predictive_stock_alerts(
        sucursal_id=sucursal_id, criticidad=criticidad
    )


@router.get(
    "/recomendaciones-traspaso-stock",
    summary="Recomendar traspasos de stock entre sucursales mediante analítica predictiva",
)
async def get_stock_transfer_recommendations(
    sucursal_id: Optional[int] = None,
    current_user: User = Depends(require_plan_capability("predicciones")),
    db: Session = Depends(get_db),
):
    """Compara demanda, cobertura y excedentes por variante dentro del tenant autenticado."""
    from app.services.ml_service import MLService

    if sucursal_id == 0:
        sucursal_id = None
    _validate_report_sucursal(db, current_user, sucursal_id)
    return MLService(db, current_user).transfer_recommendations(sucursal_id=sucursal_id)


@router.get("/alertas-stock-predictivo/excel", summary="Exportar alertas predictivas de stock en Excel (REQ-068)")
async def excel_alertas_stock_predictivo(
    sucursal_id: Optional[int] = None,
    criticidad: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ml_service import MLService

    if sucursal_id == 0:
        sucursal_id = None
    _validate_report_sucursal(db, current_user, sucursal_id)
    data = MLService(db, current_user).predictive_stock_alerts(
        sucursal_id=sucursal_id, criticidad=criticidad
    )
    headers = [
        "Producto",
        "Código",
        "Sucursal",
        "Color",
        "Talla",
        "Stock Actual",
        "Velocidad Diaria",
        "Días Cobertura",
        "Criticidad",
        "Reposición Sugerida",
    ]
    rows = [
        [
            item["producto"],
            item["codigo"],
            item["sucursal"],
            item["color"],
            item["talla"],
            item["stock_actual"],
            item["velocidad_diaria"],
            item["dias_cobertura"],
            item["criticidad"],
            item["reposicion_sugerida"],
        ]
        for item in data["items"]
    ]
    srv = ReportService(db, current_user)
    buf = srv.build_generic_excel(
        "Alertas Stock",
        "Reporte Predictivo de Agotamiento de Stock",
        headers,
        rows,
    )
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="alertas_stock_predictivo.xlsx"'},
    )


@router.get("/alertas-stock-predictivo/pdf", summary="Exportar alertas predictivas de stock en PDF (REQ-068)")
async def pdf_alertas_stock_predictivo(
    sucursal_id: Optional[int] = None,
    criticidad: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.ml_service import MLService

    if sucursal_id == 0:
        sucursal_id = None
    _validate_report_sucursal(db, current_user, sucursal_id)
    data = MLService(db, current_user).predictive_stock_alerts(
        sucursal_id=sucursal_id, criticidad=criticidad
    )
    headers = ["Producto", "Código", "Sucursal", "Talla", "Stock", "Días", "Alerta", "Sugerido"]
    rows = [
        [
            item["producto"],
            item["codigo"],
            item["sucursal"],
            item["talla"],
            str(item["stock_actual"]),
            f"{item['dias_cobertura']:.1f}d" if item["dias_cobertura"] < 900 else ">90d",
            item["criticidad"],
            f"+{item['reposicion_sugerida']} un.",
        ]
        for item in data["items"]
    ]
    srv = ReportService(db, current_user)
    buf = srv.build_generic_pdf(
        "Alertas Predictivas de Stock",
        headers,
        rows,
        [130, 60, 80, 45, 45, 45, 55, 55],
    )
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="alertas_stock_predictivo.pdf"'},
    )


# ==========================================
# 8 NUEVOS REPORTES DINÁMICOS (PUNTO 11)
# ==========================================

# 1. Más vendidos
@router.get("/mas-vendidos/preview")
async def preview_mas_vendidos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_mas_vendidos_data()
    return {"total_registros": len(data), "items": data}

@router.get("/mas-vendidos/excel")
async def excel_mas_vendidos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_mas_vendidos_data()
    headers = ["Producto", "Unidades Vendidas", "Total Recaudado (Bs.)"]
    rows = [[d["producto"], d["unidades_vendidas"], d["total_recaudado"]] for d in data]
    buf = srv.build_generic_excel("Mas Vendidos", "Reporte de Productos Más Vendidos", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="productos_mas_vendidos.xlsx"'})

@router.get("/mas-vendidos/pdf")
async def pdf_mas_vendidos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_mas_vendidos_data()
    headers = ["Producto", "Unidades", "Total (Bs.)"]
    rows = [[d["producto"], d["unidades_vendidas"], f"Bs. {d['total_recaudado']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Productos Más Vendidos", headers, rows, [280, 100, 120])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="productos_mas_vendidos.pdf"'})

# 2. Ventas por producto
@router.get("/ventas-producto/preview")
async def preview_ventas_producto(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_ventas_por_producto_data()
    return {"total_registros": len(data), "items": data}

@router.get("/ventas-producto/excel")
async def excel_ventas_producto(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_ventas_por_producto_data()
    headers = ["Producto", "Color", "Talla", "Unidades", "Subtotal (Bs.)"]
    rows = [[d["producto"], d["color"], d["talla"], d["unidades"], d["subtotal"]] for d in data]
    buf = srv.build_generic_excel("Ventas Producto", "Ventas Agrupadas por Producto", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="ventas_por_producto.xlsx"'})

@router.get("/ventas-producto/pdf")
async def pdf_ventas_producto(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_ventas_por_producto_data()
    headers = ["Producto", "Color", "Talla", "Unidades", "Subtotal (Bs.)"]
    rows = [[d["producto"][:22], d["color"][:10], d["talla"], d["unidades"], f"Bs. {d['subtotal']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Ventas Agrupadas por Producto", headers, rows, [190, 80, 50, 60, 100])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="ventas_por_producto.pdf"'})

# 3. Ventas por tipo
@router.get("/ventas-tipo/preview")
async def preview_ventas_tipo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_ventas_por_tipo_data()
    return {"total_registros": len(data), "items": data}

@router.get("/ventas-tipo/excel")
async def excel_ventas_tipo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_ventas_por_tipo_data()
    headers = ["Canal / Tipo de Venta", "Cantidad de Órdenes", "Monto Total (Bs.)"]
    rows = [[d["tipo_venta"], d["total_ordenes"], d["total_monto"]] for d in data]
    buf = srv.build_generic_excel("Ventas Tipo", "Ventas por Canal / Tipo", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="ventas_por_tipo.xlsx"'})

@router.get("/ventas-tipo/pdf")
async def pdf_ventas_tipo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_ventas_por_tipo_data()
    headers = ["Canal de Venta", "Total Órdenes", "Recaudación (Bs.)"]
    rows = [[d["tipo_venta"], d["total_ordenes"], f"Bs. {d['total_monto']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Ventas por Canal / Tipo", headers, rows, [200, 120, 160])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="ventas_por_tipo.pdf"'})

# 4. Clientes registrados
@router.get("/clientes/preview")
async def preview_clientes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_clientes_registrados_data()
    return {"total_registros": len(data), "items": data}

@router.get("/clientes/excel")
async def excel_clientes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_clientes_registrados_data()
    headers = ["Código", "Nombre", "Correo Electrónico", "Teléfono", "Total Compras", "Gasto Total (Bs.)"]
    rows = [[d["codigo"], d["nombre"], d["email"], d["telefono"], d["total_compras"], d["monto_gastado"]] for d in data]
    buf = srv.build_generic_excel("Clientes", "Clientes Registrados con Actividad", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="clientes_registrados.xlsx"'})

@router.get("/clientes/pdf")
async def pdf_clientes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_clientes_registrados_data()
    headers = ["Código", "Nombre / Correo", "Teléfono", "Compras", "Total (Bs.)"]
    rows = [[d["codigo"], f"{d['nombre']}\n{d['email']}", d["telefono"], d["total_compras"], f"Bs. {d['monto_gastado']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Clientes Registrados", headers, rows, [75, 175, 80, 60, 90])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="clientes_registrados.pdf"'})

# 5. Empleados por sucursal
@router.get("/empleados/preview")
async def preview_empleados(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_empleados_por_sucursal_data(sucursal_id)
    return {"total_registros": len(data), "items": data}

@router.get("/empleados/excel")
async def excel_empleados(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_empleados_por_sucursal_data(sucursal_id)
    headers = ["Código", "Nombre", "Correo", "Sucursal", "Teléfono", "Sueldo (Bs.)"]
    rows = [[d["codigo"], d["nombre"], d["email"], d["sucursal"], d["telefono"], d["sueldo"]] for d in data]
    buf = srv.build_generic_excel("Empleados", "Personal y Empleados por Sucursal", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="empleados_sucursal.xlsx"'})

@router.get("/empleados/pdf")
async def pdf_empleados(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_empleados_por_sucursal_data(sucursal_id)
    headers = ["Código", "Nombre", "Sucursal", "Teléfono", "Sueldo (Bs.)"]
    rows = [[d["codigo"], d["nombre"][:20], d["sucursal"], d["telefono"], f"Bs. {d['sueldo']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Personal y Empleados por Sucursal", headers, rows, [80, 150, 110, 80, 80])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="empleados_sucursal.pdf"'})

# 6. Rotación de prendas
@router.get("/rotacion/preview")
async def preview_rotacion(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_rotacion_prendas_data()
    return data

@router.get("/rotacion/excel")
async def excel_rotacion(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_rotacion_prendas_data()
    headers = ["Categoría", "Prenda", "Unidades Vendidas", "Total (Bs.)"]
    rows = []
    for m in data["mas_vendidas"]:
        rows.append(["MÁS VENDIDA", m["producto"], m["unidades_vendidas"], m["total_recaudado"]])
    for me in data["menos_vendidas"]:
        rows.append(["MENOS VENDIDA", me["producto"], me["unidades_vendidas"], me["total_recaudado"]])
    buf = srv.build_generic_excel("Rotacion", "Rotación de Prendas (Top y Menor Venta)", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="rotacion_prendas.xlsx"'})

@router.get("/rotacion/pdf")
async def pdf_rotacion(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_rotacion_prendas_data()
    headers = ["Categoría", "Prenda", "Unidades", "Total (Bs.)"]
    rows = []
    for m in data["mas_vendidas"]:
        rows.append(["TOP VENTA", m["producto"][:25], m["unidades_vendidas"], f"Bs. {m['total_recaudado']:.2f}"])
    for me in data["menos_vendidas"]:
        rows.append(["BAJA VENTA", me["producto"][:25], me["unidades_vendidas"], f"Bs. {me['total_recaudado']:.2f}"])
    buf = srv.build_generic_pdf("Rotación de Prendas (Top y Menor Venta)", headers, rows, [100, 200, 80, 100])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="rotacion_prendas.pdf"'})

# 7. Envíos Delivery StyleStore
@router.get("/envios/preview")
async def preview_envios(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_envios_report_data()
    return {"total_registros": len(data), "items": data}

@router.get("/envios/excel")
async def excel_envios(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_envios_report_data()
    headers = ["Ticket", "Cliente", "Ciudad", "Dirección", "Conductor", "Tracking Delivery", "Estado", "Costo (Bs.)", "Fecha"]
    rows = [[d["ticket"], d["cliente"], d["ciudad"], d["direccion"], d["conductor"], d["tracking"], d["estado"], d["costo"], d["fecha"]] for d in data]
    buf = srv.build_generic_excel("Envios", "Reporte de Despachos y Envíos Delivery StyleStore", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="envios_delivery.xlsx"'})

@router.get("/envios/pdf")
async def pdf_envios(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_envios_report_data()
    headers = ["Ticket", "Cliente", "Destino", "Tracking / Conductor", "Estado", "Costo"]
    rows = [[d["ticket"], d["cliente"][:15], f"{d['ciudad']} - {d['direccion'][:18]}", f"{d['tracking']}\n{d['conductor']}", d["estado"], f"Bs. {d['costo']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Reporte de Despachos y Envíos Delivery StyleStore", headers, rows, [80, 85, 140, 95, 55, 45])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="envios_delivery.pdf"'})

# 8. Devoluciones y Cambios
@router.get("/devoluciones/preview")
async def preview_devoluciones(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_cambios_devoluciones_report_data(sucursal_id)
    return {"total_registros": len(data), "items": data}

@router.get("/devoluciones/excel")
async def excel_devoluciones(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_cambios_devoluciones_report_data(sucursal_id)
    headers = ["ID", "Ticket", "Tipo", "Motivo", "Producto", "Sucursal", "Estado", "Fecha Programada"]
    rows = [[d["id"], d["ticket"], d["tipo"], d["motivo"], d["producto"], d["sucursal"], d["estado"], d["fecha_programada"]] for d in data]
    buf = srv.build_generic_excel("Devoluciones", "Reporte de Cambios y Devoluciones de Clientes", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="cambios_devoluciones.xlsx"'})

@router.get("/devoluciones/pdf")
async def pdf_devoluciones(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_cambios_devoluciones_report_data(sucursal_id)
    headers = ["Ticket", "Tipo", "Motivo", "Producto", "Sucursal", "Estado", "Fecha"]
    rows = [[d["ticket"], d["tipo"], d["motivo"], d["producto"][:18], d["sucursal"], d["estado"], d["fecha_programada"]] for d in data]
    buf = srv.build_generic_pdf("Reporte de Cambios y Devoluciones", headers, rows, [75, 55, 75, 110, 80, 60, 65])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="cambios_devoluciones.pdf"'})


# ==========================================
# REPORTES ESPECIALIZADOS FALTANTES (PUNTO 6)
# ==========================================

# 9. Flujo Financiero y Pagos
@router.get("/financiero/preview")
async def preview_financiero(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_financiero_report_data(sucursal_id)
    return {"total_registros": len(data), "items": data}

@router.get("/financiero/excel")
async def excel_financiero(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_financiero_report_data(sucursal_id)
    headers = ["Método de Pago", "N° Transacciones", "Total Recaudado (Bs.)"]
    rows = [[d["metodo"], d["cantidad_transacciones"], d["total_recaudado"]] for d in data]
    buf = srv.build_generic_excel("Financiero", "Reporte Financiero y Flujo de Pagos", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="reporte_financiero.xlsx"'})

@router.get("/financiero/pdf")
async def pdf_financiero(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_financiero_report_data(sucursal_id)
    headers = ["Método de Pago", "Transacciones", "Total Recaudado (Bs.)"]
    rows = [[d["metodo"], d["cantidad_transacciones"], f"Bs. {d['total_recaudado']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Reporte Financiero y Flujo de Pagos", headers, rows, [180, 140, 160])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="reporte_financiero.pdf"'})


# 10. Caducidad y Obsolescencia de Temporadas
@router.get("/caducidad/preview")
async def preview_caducidad(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_caducidad_report_data(sucursal_id)
    return {"total_registros": len(data), "items": data}

@router.get("/caducidad/excel")
async def excel_caducidad(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_caducidad_report_data(sucursal_id)
    headers = ["Código", "Producto", "Temporada", "Sucursal", "Talla", "Stock", "Precio (Bs.)", "Sugerencia"]
    rows = [[d["codigo"], d["producto"], d["temporada"], d["sucursal"], d["talla"], d["unidades_stock"], d["precio_actual"], d["descuento_sugerido"]] for d in data]
    buf = srv.build_generic_excel("Caducidad", "Prendas de Temporadas Pasadas / Liquidación", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="reporte_caducidad.xlsx"'})

@router.get("/caducidad/pdf")
async def pdf_caducidad(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_caducidad_report_data(sucursal_id)
    headers = ["Código", "Prenda", "Temporada", "Sucursal", "Stock", "Precio"]
    rows = [[d["codigo"], d["producto"][:20], d["temporada"][:12], d["sucursal"][:12], d["unidades_stock"], f"Bs. {d['precio_actual']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Prendas en Liquidación / Temporadas Pasadas", headers, rows, [70, 140, 80, 80, 50, 60])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="reporte_caducidad.pdf"'})


# 11. Auditoría y Bitácora
@router.get("/auditoria/preview")
async def preview_auditoria(limit: int = 150, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_auditoria_report_data(limit)
    return {"total_registros": len(data), "items": data}

@router.get("/auditoria/excel")
async def excel_auditoria(limit: int = 200, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_auditoria_report_data(limit)
    headers = ["ID", "Usuario / Rol", "Módulo", "Acción Realizada", "IP", "Fecha"]
    rows = [[d["id"], d["usuario"], d["modulo"], d["accion"], d["ip"], d["fecha"]] for d in data]
    buf = srv.build_generic_excel("Auditoria", "Registro de Bitácora de Auditoría", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="bitacora_auditoria.xlsx"'})

@router.get("/auditoria/pdf")
async def pdf_auditoria(limit: int = 150, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    srv = ReportService(db, current_user)
    data = srv.get_auditoria_report_data(limit)
    headers = ["Usuario", "Módulo", "Acción Realizada", "Fecha"]
    rows = [[d["usuario"][:18], d["modulo"][:10], d["accion"][:35], d["fecha"]] for d in data]
    buf = srv.build_generic_pdf("Bitácora de Auditoría", headers, rows, [110, 70, 200, 100])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="bitacora_auditoria.pdf"'})


# 12. Compras a Proveedores (Abastecimiento)
@router.get("/compras/preview")
async def preview_compras(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_compras_report_data(sucursal_id)
    return {"total_registros": len(data), "items": data}

@router.get("/compras/excel")
async def excel_compras(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_compras_report_data(sucursal_id)
    headers = ["ID Compra", "Fecha", "Proveedor", "Sucursal Destino", "Monto Total (Bs.)"]
    rows = [[d["id"], d["fecha"], d["proveedor"], d["sucursal"], d["total"]] for d in data]
    buf = srv.build_generic_excel("Compras", "Compras y Abastecimiento de Proveedores", headers, rows)
    return Response(content=buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="compras_proveedores.xlsx"'})

@router.get("/compras/pdf")
async def pdf_compras(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_report_sucursal(db, current_user, sucursal_id)
    srv = ReportService(db, current_user)
    data = srv.get_compras_report_data(sucursal_id)
    headers = ["ID", "Fecha", "Proveedor", "Sucursal", "Total (Bs.)"]
    rows = [[d["id"], d["fecha"], d["proveedor"][:20], d["sucursal"], f"Bs. {d['total']:.2f}"] for d in data]
    buf = srv.build_generic_pdf("Compras y Abastecimiento a Proveedores", headers, rows, [40, 80, 180, 100, 80])
    return Response(content=buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="compras_proveedores.pdf"'})


# ==========================================
# 13. COMPARATIVA ENTRE SUCURSALES (REQ-063)
# ==========================================
@router.get("/comparativa-sucursales/preview", summary="Previsualizar comparativa entre sucursales del tenant")
async def preview_comparativa_sucursales(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    srv = ReportService(db, current_user)
    return srv.get_comparativa_sucursales_data()


@router.get("/comparativa-sucursales/excel", summary="Exportar comparativa de sucursales en Excel (.xlsx)")
async def excel_comparativa_sucursales(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    srv = ReportService(db, current_user)
    buf = srv.generate_comparativa_excel()
    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Exportó reporte comparativo de sucursales en Excel (.xlsx)",
        module="reportes",
    )
    filename = f"comparativa_sucursales_{date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/comparativa-sucursales/pdf", summary="Exportar comparativa de sucursales en PDF (.pdf)")
async def pdf_comparativa_sucursales(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    srv = ReportService(db, current_user)
    buf = srv.generate_comparativa_pdf()
    BitacoraService.registrar(
        db=db,
        user=current_user,
        action="Exportó reporte comparativo de sucursales en PDF (.pdf)",
        module="reportes",
    )
    filename = f"comparativa_sucursales_{date.today().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# Aliases defensivos para garantizar compatibilidad con frontend y no dar jamás 404
@router.get("/vendedores/preview")
async def alias_preview_vendedores(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await preview_empleados(sucursal_id=sucursal_id, current_user=current_user, db=db)

@router.get("/vendedores/excel")
async def alias_excel_vendedores(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await excel_empleados(sucursal_id=sucursal_id, current_user=current_user, db=db)

@router.get("/vendedores/pdf")
async def alias_pdf_vendedores(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await pdf_empleados(sucursal_id=sucursal_id, current_user=current_user, db=db)

@router.get("/garantias/preview")
async def alias_preview_garantias(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await preview_devoluciones(sucursal_id=sucursal_id, current_user=current_user, db=db)

@router.get("/garantias/excel")
async def alias_excel_garantias(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await excel_devoluciones(sucursal_id=sucursal_id, current_user=current_user, db=db)

@router.get("/garantias/pdf")
async def alias_pdf_garantias(sucursal_id: Optional[int] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await pdf_devoluciones(sucursal_id=sucursal_id, current_user=current_user, db=db)


# ==========================================================
# ASISTENTE DE INTELIGENCIA ARTIFICIAL PARA REPORTES & VOZ
# ==========================================================
from pydantic import BaseModel, Field
from app.core.exceptions import ForbiddenException
from app.services.plan_service import PlanService
from app.services.report_ai_service import ReportAIService


class ConsultaReporteIARequest(BaseModel):
    pregunta: str = Field(min_length=3, max_length=500)


class ExportarReporteIARequest(BaseModel):
    pregunta: str = Field(min_length=3, max_length=500)
    respuesta: str = Field(min_length=1, max_length=20000)
    kpis: Optional[list] = None


def _require_ai_reports(current_user: User, db: Session) -> None:
    if not current_user.is_platform_admin and current_user.role not in {
        "administrador",
        "encargado",
        "encargado_sucursal",
    }:
        raise ForbiddenException(
            "Los reportes con IA requieren un rol administrativo autorizado."
        )
    PlanService(db).require_capability(current_user, "ia_generativa")


@router.post("/asistente-ia", summary="Consulta ejecutiva analítica con IA para administradores y encargados")
async def consultar_asistente_ia(
    req: ConsultaReporteIARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Procesa una consulta gerencial o analítica de reportes usando IA Groq y contexto operativo."""
    _require_ai_reports(current_user, db)
    try:
        service = ReportAIService(db, current_user)
        user_name = current_user.name or "Administrador"
        resultado = service.procesar_consulta(pregunta=req.pregunta, user_name=user_name)

        BitacoraService.registrar(
            db=db,
            user=current_user,
            action=f"Consultó asistente de IA para reportes: '{req.pregunta[:60]}'",
            module="reportes",
        )

        return resultado
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "pregunta": req.pregunta,
            "respuesta": "No se pudo completar la consulta analítica en este momento. Por favor verifica los filtros o intenta con otra pregunta.",
            "kpis": [],
            "ia_powered": False,
            "modo_ia": "error",
            "proveedor_ia": "ninguno",
        }


@router.get("/asistente-ia/estado", summary="Estado del motor híbrido de IA")
async def estado_asistente_ia(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.config import settings
    _require_ai_reports(current_user, db)
    return {
        "modo_preferido": "online_groq" if bool(settings.GROQ_API_KEY) else "online_local",
        "groq_configurado": bool(settings.GROQ_API_KEY),
        "modelo_groq": settings.GROQ_MODEL if settings.GROQ_API_KEY else None,
        "fallback_servidor": "motor_analitico_local",
        "fallback_sin_conexion": "cache_local_del_tenant",
    }


@router.get("/asistente-ia/snapshot", summary="Actualizar datos locales para consultas sin conexión")
async def snapshot_asistente_ia(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_ai_reports(current_user, db)
    return ReportAIService(db, current_user).obtener_snapshot_offline()


@router.post("/asistente-ia/excel", summary="Exportar consulta analítica de IA a archivo Excel (.xlsx)")
async def exportar_asistente_ia_excel(
    req: ExportarReporteIARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera y descarga un Excel con la consulta y la respuesta analítica del Asistente IA."""
    _require_ai_reports(current_user, db)
    service = ReportAIService(db, current_user)
    buf = service.exportar_excel(req.pregunta, req.respuesta, req.kpis or [])

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Exportó reporte IA a Excel: '{req.pregunta[:50]}'",
        module="reportes",
    )

    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reporte_ejecutivo_ia.xlsx"'},
    )


@router.post("/asistente-ia/pdf", summary="Exportar consulta analítica de IA a archivo PDF (.pdf)")
async def exportar_asistente_ia_pdf(
    req: ExportarReporteIARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genera y descarga un PDF estilizado con la consulta y respuesta del Asistente IA."""
    _require_ai_reports(current_user, db)
    service = ReportAIService(db, current_user)
    buf = service.exportar_pdf(req.pregunta, req.respuesta, req.kpis or [])

    BitacoraService.registrar(
        db=db,
        user=current_user,
        action=f"Exportó reporte IA a PDF: '{req.pregunta[:50]}'",
        module="reportes",
    )

    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reporte_ejecutivo_ia.pdf"'},
    )
