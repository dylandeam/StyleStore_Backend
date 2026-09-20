"""
Endpoints de Cambios y Devoluciones (v6 Punto 9).
"""
from datetime import date, time
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.empleado import Empleado
from app.services.cambio_service import CambioService
from app.api.deps import get_current_user

router = APIRouter(prefix="/cambios", tags=["Cambios y Devoluciones"])


class SolicitarCambioRequest(BaseModel):
    orden_venta_id: int
    detalle_venta_id: int
    tipo: str = Field(..., pattern="^(cambio|devolucion)$")
    motivo: str
    sucursal_id: int
    fecha_programada: date
    hora_programada: Optional[time] = None
    descripcion_problema: str
    producto_nuevo_codigo: Optional[str] = None
    talla_nueva_id: Optional[int] = None
    color_nuevo_id: Optional[int] = None


class ResponderCambioRequest(BaseModel):
    nuevo_estado: str = Field(..., pattern="^(aceptada|rechazada)$")
    respuesta_encargado: str


class CompletarCajaRequest(BaseModel):
    reponer_prenda_original: bool = True
    nuevo_stock_inventario_id: Optional[int] = None


@router.post("", summary="Registrar solicitud de cambio o devolución (Cliente)")
async def solicitar_cambio(
    payload: SolicitarCambioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CambioService(db)
    solicitud = service.solicitar_cambio_devolucion(
        user=current_user,
        orden_venta_id=payload.orden_venta_id,
        detalle_venta_id=payload.detalle_venta_id,
        tipo=payload.tipo,
        motivo=payload.motivo,
        sucursal_id=payload.sucursal_id,
        fecha_programada=payload.fecha_programada,
        descripcion_problema=payload.descripcion_problema,
        hora_programada=payload.hora_programada,
        producto_nuevo_codigo=payload.producto_nuevo_codigo,
        talla_nueva_id=payload.talla_nueva_id,
        color_nuevo_id=payload.color_nuevo_id,
    )
    return {
        "status": "ok",
        "solicitud_id": solicitud.id,
        "mensaje": "Solicitud de cambio o devolución registrada exitosamente.",
    }


@router.get("/mis-solicitudes", summary="Listar solicitudes del cliente autenticado")
async def get_mis_solicitudes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CambioService(db)
    items = service.listar_mis_solicitudes(user=current_user)
    resultado = []
    for s in items:
        resultado.append({
            "id": s.id,
            "orden_venta_id": s.orden_venta_id,
            "ticket_numero": s.orden_venta.ticket_numero if s.orden_venta else f"ORD-{s.orden_venta_id}",
            "fecha_compra": s.orden_venta.fecha.strftime("%d/%m/%Y") if (s.orden_venta and s.orden_venta.fecha) else "",
            "tipo": s.tipo,
            "motivo": s.motivo,
            "sucursal_nombre": s.sucursal.nombre if s.sucursal else "-",
            "fecha_programada": s.fecha_programada.strftime("%d/%m/%Y") if s.fecha_programada else "",
            "hora_programada": s.hora_programada.strftime("%H:%M") if s.hora_programada else None,
            "descripcion_problema": s.descripcion_problema,
            "estado": s.estado,
            "respuesta_encargado": s.respuesta_encargado,
            "producto_original": s.detalle_venta.producto_nombre if s.detalle_venta else "-",
            "color_original": s.detalle_venta.color_nombre if s.detalle_venta else "-",
            "talla_original": s.detalle_venta.talla_nombre if s.detalle_venta else "-",
            "producto_nuevo": s.producto_nuevo.nombre if s.producto_nuevo else None,
            "talla_nueva": s.talla_nueva.nombre if s.talla_nueva else None,
            "color_nuevo": s.color_nuevo.nombre if s.color_nuevo else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return resultado


@router.get("", summary="Listar solicitudes para administradores y encargados de sucursal")
async def listar_solicitudes_staff(
    sucursal_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["administrador", "encargado", "vendedor"]:
        raise HTTPException(status_code=403, detail="Acceso denegado a personal autorizado.")

    # Encargado de sucursal: por defecto su sucursal si no especifica
    if current_user.role in ["encargado", "vendedor"] and sucursal_id is None:
        empleado = db.query(Empleado).filter(Empleado.user_id == current_user.id).first()
        if empleado:
            sucursal_id = empleado.sucursal_id

    # Si sucursal_id es 0, ver todas
    if sucursal_id == 0:
        sucursal_id = None

    service = CambioService(db)
    items = service.listar_solicitudes(sucursal_id=sucursal_id, estado=estado, limit=limit, offset=offset)
    resultado = []
    for s in items:
        cliente_nombre = "Cliente General"
        cliente_email = "-"
        if s.orden_venta and s.orden_venta.cliente:
            c = s.orden_venta.cliente
            if c.user:
                cliente_nombre = f"{c.user.name} {c.user.apellido or ''}".strip()
                cliente_email = c.user.email
            elif hasattr(c, "nombre"):
                cliente_nombre = c.nombre or cliente_nombre

        resultado.append({
            "id": s.id,
            "orden_venta_id": s.orden_venta_id,
            "ticket_numero": s.orden_venta.ticket_numero if s.orden_venta else f"ORD-{s.orden_venta_id}",
            "cliente_nombre": cliente_nombre,
            "cliente_email": cliente_email,
            "tipo": s.tipo,
            "motivo": s.motivo,
            "sucursal_id": s.sucursal_id,
            "sucursal_nombre": s.sucursal.nombre if s.sucursal else "-",
            "fecha_programada": s.fecha_programada.strftime("%d/%m/%Y") if s.fecha_programada else "",
            "hora_programada": s.hora_programada.strftime("%H:%M") if s.hora_programada else None,
            "descripcion_problema": s.descripcion_problema,
            "estado": s.estado,
            "respuesta_encargado": s.respuesta_encargado,
            "producto_original": s.detalle_venta.producto_nombre if s.detalle_venta else "-",
            "color_original": s.detalle_venta.color_nombre if s.detalle_venta else "-",
            "talla_original": s.detalle_venta.talla_nombre if s.detalle_venta else "-",
            "producto_nuevo": s.producto_nuevo.nombre if s.producto_nuevo else None,
            "talla_nueva": s.talla_nueva.nombre if s.talla_nueva else None,
            "color_nuevo": s.color_nuevo.nombre if s.color_nuevo else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return resultado


@router.put("/{solicitud_id}/responder", summary="Aceptar o rechazar solicitud (Encargado/Admin)")
async def responder_solicitud(
    solicitud_id: int,
    payload: ResponderCambioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["administrador", "encargado"]:
        raise HTTPException(status_code=403, detail="Solo administradores y encargados pueden responder solicitudes.")

    service = CambioService(db)
    solicitud = service.responder_solicitud(
        solicitud_id=solicitud_id,
        nuevo_estado=payload.nuevo_estado,
        respuesta_encargado=payload.respuesta_encargado,
    )
    return {"status": "ok", "estado": solicitud.estado, "mensaje": "Respuesta enviada exitosamente al cliente."}


@router.post("/{solicitud_id}/completar", summary="Completar canje en caja física y ajustar stock")
async def completar_en_caja(
    solicitud_id: int,
    payload: CompletarCajaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ["administrador", "encargado", "vendedor"]:
        raise HTTPException(status_code=403, detail="Acceso denegado a personal de caja.")

    service = CambioService(db)
    solicitud = service.completar_en_caja(
        solicitud_id=solicitud_id,
        reponer_prenda_original=payload.reponer_prenda_original,
        nuevo_stock_inventario_id=payload.nuevo_stock_inventario_id,
    )
    return {"status": "ok", "estado": solicitud.estado, "mensaje": "Cambio/Devolución completado en caja con ajuste de stock."}


@router.get("/opciones-disponibles", summary="Obtener tallas con stock y colores de la prenda para cambio (Punto 5)")
async def get_opciones_disponibles(
    producto_codigo: str,
    sucursal_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna los colores existentes para la prenda y únicamente las tallas que tienen stock
    disponible en la sucursal donde se realizó la compra original.
    """
    from app.models.producto import Producto
    from app.models.stock_inventario import StockInventario
    from app.models.producto_color import ProductoColor
    from sqlalchemy import func

    p = db.query(Producto).filter(func.lower(Producto.codigo) == producto_codigo.strip().lower()).first()
    if not p:
        return {"colores": [], "tallas": []}

    # Colores existentes para esa prenda (Producto_Color)
    colores = []
    seen_colores = set()
    for pc in p.colores_rel:
        if pc.color and pc.color.id not in seen_colores:
            seen_colores.add(pc.color.id)
            colores.append({
                "id": pc.color.id,
                "nombre": pc.color.nombre,
                "codigo_hex": getattr(pc.color, "codigo_hex", None) or getattr(pc.color, "hex", None),
            })

    # Tallas con stock disponible en la sucursal de la compra original
    stocks = (
        db.query(StockInventario)
        .join(ProductoColor, StockInventario.producto_color_id == ProductoColor.id)
        .filter(
            ProductoColor.producto_codigo == p.codigo,
            StockInventario.sucursal_id == sucursal_id,
            StockInventario.cantidad > 0,
        )
        .all()
    )

    tallas_map = {}
    for s in stocks:
        if s.talla and s.talla.id not in tallas_map:
            tallas_map[s.talla.id] = {
                "id": s.talla.id,
                "nombre": s.talla.nombre,
                "cantidad": s.cantidad,
                "stock_inventario_id": s.id,
                "color_id": s.producto_color.color_id if s.producto_color else None,
            }

    return {
        "colores": colores,
        "tallas": list(tallas_map.values()),
    }

