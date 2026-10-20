"""Idempotent synchronization contract for web and mobile offline queues."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.reservas import create_reserva
from app.api.v1.ventas import create_venta_presencial
from app.core.exceptions import ForbiddenException
from app.database import get_db
from app.models.orden_venta import OrdenVenta
from app.models.permission import Permission
from app.models.reserva import Reserva
from app.models.role_permission import RolePermission
from app.models.sync_operation import SyncOperation
from app.models.user import User
from app.schemas.pago_envio import VentaPresencialCreate
from app.schemas.reserva import ReservaCreate
from app.schemas.sync import SyncBatchRequest, SyncOperationRequest, SyncOperationResponse

router = APIRouter(prefix="/sync", tags=["Sincronización offline"])


def _response(record: SyncOperation) -> SyncOperationResponse:
    return SyncOperationResponse.model_validate(record)


def _can_register_sale(db: Session, user: User) -> bool:
    if user.role in ["administrador", "encargado_sucursal"]:
        return True
    filters = [Permission.code == "productos.editar"]
    if user.role_id:
        filters.append((RolePermission.role_id == user.role_id) | (RolePermission.role == user.role))
    else:
        filters.append(RolePermission.role == user.role)
    return db.query(RolePermission).join(Permission, RolePermission.permission_id == Permission.id).filter(*filters).first() is not None


def _find_owned(db: Session, operation_uuid: str, user: User) -> SyncOperation | None:
    return _find_owned_ids(db, operation_uuid, user.empresa_id, user.id)


def _find_owned_ids(db: Session, operation_uuid: str, empresa_id: int | None, user_id: int) -> SyncOperation | None:
    return db.query(SyncOperation).filter(
        SyncOperation.operation_uuid == operation_uuid,
        SyncOperation.empresa_id == empresa_id,
        SyncOperation.user_id == user_id,
    ).first()


def _reconcile_processing(db: Session, record: SyncOperation) -> SyncOperation:
    if record.status != "procesando":
        return record
    if record.operation_type == "reserva":
        resource = db.query(Reserva).filter(Reserva.client_operation_uuid == record.operation_uuid).first()
        result_type = "reserva"
    else:
        resource = db.query(OrdenVenta).filter(OrdenVenta.client_operation_uuid == record.operation_uuid).first()
        result_type = "venta"
    if resource:
        record.status = "confirmada"
        record.result_type = result_type
        record.result_id = resource.id
        record.reason = None
        db.commit()
        db.refresh(record)
    return record


async def _process(payload: SyncOperationRequest, user: User, db: Session) -> SyncOperationResponse:
    if user.empresa_id is None:
        raise ForbiddenException("La sincronización comercial requiere pertenecer a una empresa")

    operation_uuid = str(payload.operation_uuid)
    empresa_id = user.empresa_id
    user_id = user.id
    existing = _find_owned(db, operation_uuid, user)
    if existing:
        return _response(_reconcile_processing(db, existing))
    collision = db.query(SyncOperation.id).filter(SyncOperation.operation_uuid == operation_uuid).first()
    if collision:
        raise ForbiddenException("El identificador de operación pertenece a otro ámbito")

    sucursal_id = payload.payload.get("sucursal_id")
    record = SyncOperation(
        operation_uuid=operation_uuid,
        empresa_id=empresa_id,
        user_id=user_id,
        sucursal_id=sucursal_id if isinstance(sucursal_id, int) else None,
        operation_type=payload.operation_type,
        payload_version=payload.payload_version,
        payload=payload.payload,
        client_created_at=payload.client_created_at,
        status="procesando",
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        concurrent = _find_owned_ids(db, operation_uuid, empresa_id, user_id)
        if concurrent:
            return _response(_reconcile_processing(db, concurrent))
        raise ForbiddenException("El identificador de operación pertenece a otro ámbito")

    try:
        if payload.operation_type == "reserva":
            business_payload = ReservaCreate.model_validate({**payload.payload, "operation_uuid": operation_uuid})
            result = await create_reserva(business_payload, user, db)
            result_type = "reserva"
        else:
            if not _can_register_sale(db, user):
                raise ForbiddenException("No tiene permiso para registrar ventas de contado")
            if str(payload.payload.get("metodo_pago", "efectivo")).lower() != "efectivo":
                raise ForbiddenException("La sincronización offline solo acepta ventas en efectivo")
            clean_payload = {key: value for key, value in payload.payload.items() if key != "snapshot"}
            business_payload = VentaPresencialCreate.model_validate({**clean_payload, "operation_uuid": operation_uuid})
            result = await create_venta_presencial(business_payload, user, db)
            result_type = "venta"

        record = _find_owned(db, operation_uuid, user)
        if record is None:
            raise RuntimeError("No se pudo recuperar la operación sincronizada")
        record.status = "confirmada"
        record.result_type = result_type
        record.result_id = int(result["id"])
        record.reason = None
        db.commit()
        db.refresh(record)
        return _response(record)
    except (HTTPException, ValidationError) as error:
        detail = error.detail if isinstance(error, HTTPException) else "El contenido local no cumple el contrato vigente"
        rejected = _find_owned_ids(db, operation_uuid, empresa_id, user_id)
        if rejected is None:
            rejected = SyncOperation(
                operation_uuid=operation_uuid,
                empresa_id=empresa_id,
                user_id=user_id,
                sucursal_id=sucursal_id if isinstance(sucursal_id, int) else None,
                operation_type=payload.operation_type,
                payload_version=payload.payload_version,
                payload=payload.payload,
                client_created_at=payload.client_created_at,
            )
            db.add(rejected)
        rejected.status = "conflicto" if isinstance(error, HTTPException) and error.status_code in (400, 404, 409) else "rechazada"
        rejected.reason = str(detail)
        db.commit()
        db.refresh(rejected)
        return _response(rejected)


@router.post("/operations", response_model=SyncOperationResponse)
async def sync_operation(
    payload: SyncOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _process(payload, current_user, db)


@router.post("/batch", response_model=list[SyncOperationResponse])
async def sync_batch(
    payload: SyncBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [await _process(operation, current_user, db) for operation in payload.operations]


@router.get("/operations", response_model=list[SyncOperationResponse])
async def list_sync_operations(
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SyncOperation).filter(SyncOperation.user_id == current_user.id)
    if current_user.empresa_id is not None:
        query = query.filter(SyncOperation.empresa_id == current_user.empresa_id)
    if status:
        query = query.filter(SyncOperation.status == status)
    return [_response(item) for item in query.order_by(SyncOperation.created_at.desc()).all()]
