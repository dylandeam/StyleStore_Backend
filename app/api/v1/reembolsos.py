"""Cash refund workflow for offline sales rejected by the central stock."""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenException, NotFoundException
from app.database import get_db
from app.models.reembolso_offline import ReembolsoOffline
from app.models.user import User
from app.services.tenant_scope import effective_empresa_id
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/reembolsos", tags=["Reembolsos offline"])


class RefundUpdate(BaseModel):
    estado: Literal["entregado", "cancelado"]
    observaciones: str = Field(..., min_length=3, max_length=1000)


def _serialize(item: ReembolsoOffline) -> dict:
    return {
        "id": item.id,
        "operation_uuid": item.operation_uuid,
        "empresa_id": item.empresa_id,
        "user_id": item.user_id,
        "sucursal_id": item.sucursal_id,
        "monto": float(item.monto),
        "moneda": item.moneda,
        "metodo_original": item.metodo_original,
        "estado": item.estado,
        "motivo": item.motivo,
        "observaciones": item.observaciones,
        "procesado_por": item.procesado_por,
        "procesado_at": item.procesado_at,
        "created_at": item.created_at,
    }


@router.get("/mios")
async def my_refunds(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    items = db.query(ReembolsoOffline).filter(
        ReembolsoOffline.user_id == current_user.id,
        ReembolsoOffline.empresa_id == current_user.empresa_id,
    ).order_by(ReembolsoOffline.created_at.desc()).all()
    return [_serialize(item) for item in items]


@router.get("")
async def list_refunds(
    estado: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {"administrador", "encargado_sucursal", "cajero"}:
        raise ForbiddenException("Solo el personal autorizado puede gestionar reembolsos.")
    query = db.query(ReembolsoOffline)
    empresa_id = effective_empresa_id(current_user)
    if empresa_id is not None:
        query = query.filter(ReembolsoOffline.empresa_id == empresa_id)
    if estado:
        query = query.filter(ReembolsoOffline.estado == estado)
    return [_serialize(item) for item in query.order_by(ReembolsoOffline.created_at.desc()).all()]


@router.put("/{refund_id}")
async def update_refund(
    refund_id: int,
    payload: RefundUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {"administrador", "encargado_sucursal", "cajero"}:
        raise ForbiddenException("Solo el personal autorizado puede gestionar reembolsos.")
    query = db.query(ReembolsoOffline).filter(ReembolsoOffline.id == refund_id)
    empresa_id = effective_empresa_id(current_user)
    if empresa_id is not None:
        query = query.filter(ReembolsoOffline.empresa_id == empresa_id)
    refund = query.first()
    if not refund:
        raise NotFoundException("Reembolso no encontrado.")
    if refund.estado != "pendiente":
        raise ForbiddenException("El reembolso ya fue resuelto y conserva su estado histórico.")
    refund.estado = payload.estado
    refund.observaciones = payload.observaciones.strip()
    refund.procesado_por = current_user.id
    refund.procesado_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(refund)
    BitacoraService.registrar(
        db,
        current_user,
        f"Marcó el reembolso offline #{refund.id} como {refund.estado}",
        "reembolsos",
    )
    return _serialize(refund)
