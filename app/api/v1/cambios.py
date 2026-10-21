"""
Endpoints de Cambios y Devoluciones (v6 Punto 9).
"""
from datetime import date, time
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.empleado import Empleado
from app.services.cambio_service import CambioService
from app.api.deps import get_current_user
from app.services.tenant_scope import get_scoped_sucursal
from app.models.empresa import Empresa
from app.models.stock_inventario import StockInventario
from app.models.cambio_devolucion import SaldoFavorCliente, MovimientoSaldoFavor
from app.services.tenant_scope import scope_by_sucursal
from app.services.bitacora_service import BitacoraService

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
    metodo_pago_diferencia: Optional[str] = Field(None, pattern="^(efectivo|qr)$")
    efectivo_recibido: Optional[Decimal] = Field(None, ge=0)
    metodo_reembolso: Optional[str] = Field(None, pattern="^(efectivo|transferencia)$")


class PoliticaCambiosRequest(BaseModel):
    plazo_cambios_dias: int = Field(..., ge=1, le=90)


def _campos_financieros(s):
    return {
        "nuevo_stock_inventario_id": s.nuevo_stock_inventario_id,
        "precio_original": s.precio_original if s.precio_original is not None else (s.detalle_venta.precio_unitario if s.detalle_venta else None),
        "precio_nuevo": s.precio_nuevo,
        "monto_adicional": s.monto_adicional,
        "saldo_favor_generado": s.saldo_favor_generado,
        "monto_reembolsado": s.monto_reembolsado,
        "metodo_pago_diferencia": s.metodo_pago_diferencia,
        "nota_venta_numero": s.nota_venta_numero,
        "orden_ajuste_id": s.orden_ajuste_id,
    }


@router.get("/politica", summary="Consultar plazo de cambios del tenant")
async def consultar_politica(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    return {"plazo_cambios_dias": empresa.plazo_cambios_dias if empresa else 7}


@router.put("/politica", summary="Configurar plazo de cambios del tenant")
async def actualizar_politica(payload: PoliticaCambiosRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "administrador" or current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Solo el administrador del tenant puede definir esta política.")
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")
    empresa.plazo_cambios_dias = payload.plazo_cambios_dias
    db.commit()
    return {"plazo_cambios_dias": empresa.plazo_cambios_dias, "message": "Política actualizada."}


@router.get("/mi-saldo", summary="Consultar saldo a favor del cliente en el tenant")
async def consultar_mi_saldo(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cuenta = db.query(SaldoFavorCliente).filter(
        SaldoFavorCliente.empresa_id == current_user.empresa_id,
        SaldoFavorCliente.user_id == current_user.id,
    ).first()
    movimientos = []
    if cuenta:
        movimientos = db.query(MovimientoSaldoFavor).filter(
            MovimientoSaldoFavor.saldo_favor_id == cuenta.id
        ).order_by(MovimientoSaldoFavor.created_at.desc()).limit(20).all()
    return {
        "saldo": cuenta.saldo if cuenta else Decimal("0.00"),
        "movimientos": [{
            "id": m.id, "tipo": m.tipo, "monto": m.monto,
            "saldo_resultante": m.saldo_resultante, "descripcion": m.descripcion,
            "created_at": m.created_at,
        } for m in movimientos],
    }


@router.get("/inventario-disponible", summary="Prendas disponibles para completar un cambio")
async def inventario_para_cambio(sucursal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_scoped_sucursal(db, current_user, sucursal_id)
    stocks = scope_by_sucursal(db.query(StockInventario), db, current_user, StockInventario.sucursal_id).filter(
        StockInventario.sucursal_id == sucursal_id, StockInventario.cantidad > 0
    ).all()
    return [{
        "stock_inventario_id": s.id,
        "producto_codigo": s.producto_color.producto_codigo,
        "producto_nombre": s.producto_color.producto.nombre,
        "color_nombre": s.producto_color.color.nombre if s.producto_color.color else None,
        "talla_nombre": s.talla.nombre if s.talla else None,
        "precio": s.precio_variante if s.precio_variante is not None else s.producto_color.producto.precio,
        "cantidad": s.cantidad,
    } for s in stocks if s.producto_color and s.producto_color.producto]


@router.post("", summary="Registrar solicitud de cambio o devolución (Cliente)")
async def solicitar_cambio(
    payload: SolicitarCambioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CambioService(db, current_user)
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
    service = CambioService(db, current_user)
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
            "empresa_id": s.sucursal.empresa_id if s.sucursal else None,
            "empresa_nombre": s.sucursal.empresa_rel.nombre if s.sucursal and s.sucursal.empresa_rel else None,
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
            **_campos_financieros(s),
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

    service = CambioService(db, current_user)
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
            **_campos_financieros(s),
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

    service = CambioService(db, current_user)
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

    service = CambioService(db, current_user)
    solicitud = service.completar_en_caja(
        solicitud_id=solicitud_id,
        reponer_prenda_original=payload.reponer_prenda_original,
        nuevo_stock_inventario_id=payload.nuevo_stock_inventario_id,
        metodo_pago_diferencia=payload.metodo_pago_diferencia,
        efectivo_recibido=payload.efectivo_recibido,
        metodo_reembolso=payload.metodo_reembolso,
    )
    BitacoraService.registrar(
        db=db, user=current_user, module="cambios",
        action=f"Completó solicitud #{solicitud.id}; nota {solicitud.nota_venta_numero}; adicional Bs {solicitud.monto_adicional}; saldo Bs {solicitud.saldo_favor_generado}; reembolso Bs {solicitud.monto_reembolsado}",
    )
    return {"status": "ok", "estado": solicitud.estado, "mensaje": "Cambio/Devolución completado con nota de venta.", **_campos_financieros(solicitud)}


@router.get("/opciones-disponibles", summary="Obtener tallas con stock y colores de la prenda para cambio (Punto 5)")
async def get_opciones_disponibles(
    producto_codigo: str,
    sucursal_id: int,
    current_user: User = Depends(get_current_user),
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

    get_scoped_sucursal(db, current_user, sucursal_id)
    product_query = db.query(Producto).filter(
        func.lower(Producto.codigo) == producto_codigo.strip().lower()
    )
    if not current_user.is_platform_admin:
        product_query = product_query.filter(Producto.empresa_id == current_user.empresa_id)
    p = product_query.first()
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
