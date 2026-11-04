"""Idempotent synchronization contract for web and mobile offline queues."""
from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_plan_capability
from app.api.v1.reservas import create_reserva
from app.api.v1.ventas import create_venta_presencial
from app.core.exceptions import ForbiddenException
from app.database import get_db
from app.models.orden_venta import OrdenVenta
from app.models.permission import Permission
from app.models.reserva import Reserva
from app.models.resena_producto import ResenaProducto
from app.models.role_permission import RolePermission
from app.models.role import Role
from app.models.sync_operation import SyncOperation
from app.models.reembolso_offline import ReembolsoOffline
from app.models.user import User
from app.schemas.pago_envio import VentaPresencialCreate
from app.schemas.reserva import ReservaCreate
from app.schemas.resena_producto import ResenaProductoUpsert
from app.services.resena_producto_service import ResenaProductoService
from app.services.notificacion_service import NotificacionService
from app.services.role_service import RoleService
from app.schemas.sync import (
    SyncBatchRequest,
    SyncDiagnosticoItem,
    SyncMetricasResponse,
    SyncAdminOperationItem,
    SyncAdminOperationsResponse,
    SyncOperationRequest,
    SyncOperationResponse,
)
from app.models.notificacion import Notificacion
from app.models.sucursal import Sucursal

router = APIRouter(prefix="/sync", tags=["Sincronización offline"])


def _response(record: SyncOperation, db: Session) -> SyncOperationResponse:
    response = SyncOperationResponse.model_validate(record)
    refund = db.query(ReembolsoOffline).filter(
        ReembolsoOffline.sync_operation_id == record.id
    ).first()
    if refund:
        response = response.model_copy(update={
            "refund_id": refund.id,
            "refund_status": refund.estado,
            "refund_amount": float(refund.monto),
        })
    return response


def _can_register_sale(db: Session, user: User) -> bool:
    return _has_permission(db, user, "ventas.crear")


def _has_permission(db: Session, user: User, permission_code: str) -> bool:
    if user.is_platform_admin or user.role == "administrador":
        return True
    filters = [Permission.code == permission_code]
    if user.role_id:
        filters.append(RolePermission.role_id == user.role_id)
    else:
        return False
    return (
        db.query(RolePermission)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .join(Role, RolePermission.role_id == Role.id)
        .filter(*filters)
        .filter(Role.active.is_(True), Role.empresa_id == user.empresa_id)
        .first()
        is not None
    )


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
    elif record.operation_type == "venta_efectivo":
        resource = db.query(OrdenVenta).filter(OrdenVenta.client_operation_uuid == record.operation_uuid).first()
        result_type = "venta"
    else:
        resource = db.query(ResenaProducto).filter(
            ResenaProducto.client_operation_uuid == record.operation_uuid
        ).first()
        result_type = "resena_producto"
    if resource:
        record.status = "confirmada"
        record.result_type = result_type
        record.result_id = resource.id
        record.reason = None
        db.commit()
        db.refresh(record)
    return record


def _notify_result(db: Session, record: SyncOperation, user: User) -> None:
    try:
        NotificacionService(db).notificar_resultado_operacion_offline(record, user)
    except Exception:
        # La notificación es complementaria: nunca debe revertir una operación confirmada.
        db.rollback()


def _notify_admin_incident(db: Session, record: SyncOperation) -> None:
    try:
        refund = db.query(ReembolsoOffline).filter(
            ReembolsoOffline.sync_operation_id == record.id
        ).first()
        NotificacionService(db).notificar_incidente_operacion_offline(record, refund)
    except Exception:
        db.rollback()


async def _process(payload: SyncOperationRequest, user: User, db: Session) -> SyncOperationResponse:
    if user.empresa_id is None:
        raise ForbiddenException("La sincronización comercial requiere pertenecer a una empresa")

    RoleService(db, user.empresa_id).seed_default_permissions_and_roles()
    db.refresh(user)

    operation_uuid = str(payload.operation_uuid)
    empresa_id = user.empresa_id
    user_id = user.id
    existing = _find_owned(db, operation_uuid, user)
    if existing:
        existing = _reconcile_processing(db, existing)
        _notify_result(db, existing, user)
        return _response(existing, db)
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
            return _response(_reconcile_processing(db, concurrent), db)
        raise ForbiddenException("El identificador de operación pertenece a otro ámbito")

    try:
        if payload.operation_type == "reserva":
            if not _has_permission(db, user, "reservas.crear"):
                raise ForbiddenException("Las reservas no están disponibles temporalmente en esta tienda.")
            business_payload = ReservaCreate.model_validate({**payload.payload, "operation_uuid": operation_uuid})
            result = await create_reserva(business_payload, user, db)
            result_type = "reserva"
        elif payload.operation_type == "venta_efectivo":
            if not _can_register_sale(db, user):
                raise ForbiddenException("No tiene permiso para registrar ventas de contado")
            if str(payload.payload.get("metodo_pago", "efectivo")).lower() != "efectivo":
                raise ForbiddenException("La sincronización offline solo acepta ventas en efectivo")
            clean_payload = {key: value for key, value in payload.payload.items() if key != "snapshot"}
            if clean_payload.get("codigo_cliente") in {"CLI-GENERAL", "GENERICO"}:
                clean_payload.pop("codigo_cliente", None)
            if not clean_payload.get("codigo_cliente"):
                clean_payload.setdefault("comprador_nombre", "Cliente de mostrador")
                clean_payload.setdefault("comprador_ci", "SIN-DATO")
            business_payload = VentaPresencialCreate.model_validate({**clean_payload, "operation_uuid": operation_uuid})
            result = await create_venta_presencial(business_payload, user, db)
            result_type = "venta"
        else:
            if not _has_permission(db, user, "resenas.crear"):
                raise ForbiddenException("Las reseñas no están disponibles temporalmente en esta tienda.")
            codigo = str(payload.payload.get("codigo") or "").strip()
            if not codigo:
                raise HTTPException(status_code=400, detail="La reseña no identifica una prenda")
            review_payload = ResenaProductoUpsert.model_validate(payload.payload)
            review_result = ResenaProductoService(db).upsert(
                codigo, review_payload, user, operation_uuid=operation_uuid
            )
            own_review = review_result.get("mi_resena")
            if not own_review:
                raise RuntimeError("No se pudo recuperar la reseña sincronizada")
            result = own_review
            result_type = "resena_producto"

        record = _find_owned(db, operation_uuid, user)
        if record is None:
            raise RuntimeError("No se pudo recuperar la operación sincronizada")
        record.status = "confirmada"
        record.result_type = result_type
        record.result_id = int(result["id"])
        record.reason = None
        db.commit()
        db.refresh(record)
        _notify_result(db, record, user)
        return _response(record, db)
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
        db.flush()

        reason_text = str(detail).lower()
        snapshot = payload.payload.get("snapshot") or {}
        raw_total = snapshot.get("total", 0) if isinstance(snapshot, dict) else 0
        try:
            refund_amount = Decimal(str(raw_total))
        except (InvalidOperation, TypeError, ValueError):
            refund_amount = Decimal("0")
        stock_conflict = (
            payload.operation_type == "venta_efectivo"
            and str(payload.payload.get("metodo_pago", "efectivo")).lower() == "efectivo"
            and isinstance(error, HTTPException)
            and error.status_code in (400, 409)
            and ("stock" in reason_text or "disponib" in reason_text)
            and refund_amount > 0
        )
        if stock_conflict and not db.query(ReembolsoOffline.id).filter(
            ReembolsoOffline.operation_uuid == operation_uuid
        ).first():
            db.add(ReembolsoOffline(
                empresa_id=empresa_id,
                user_id=user_id,
                sucursal_id=rejected.sucursal_id,
                sync_operation_id=rejected.id,
                operation_uuid=operation_uuid,
                monto=refund_amount,
                moneda="BOB",
                metodo_original="efectivo",
                estado="pendiente",
                motivo=str(detail),
            ))
        db.commit()
        db.refresh(rejected)
        _notify_result(db, rejected, user)
        _notify_admin_incident(db, rejected)
        return _response(rejected, db)


@router.post("/operations", response_model=SyncOperationResponse, dependencies=[Depends(require_plan_capability("offline"))])
async def sync_operation(
    payload: SyncOperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await _process(payload, current_user, db)


@router.post("/batch", response_model=list[SyncOperationResponse], dependencies=[Depends(require_plan_capability("offline"))])
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
    return [_response(item, db) for item in query.order_by(SyncOperation.created_at.desc()).all()]


@router.get(
    "/admin/operations",
    response_model=SyncAdminOperationsResponse,
    summary="Panel tenant de operaciones sincronizadas offline (CU44)",
)
async def list_admin_sync_operations(
    status: str | None = Query(None, pattern="^(procesando|confirmada|rechazada|conflicto)$"),
    operation_type: str | None = Query(None, pattern="^(reserva|venta_efectivo|resena_producto)$"),
    sucursal_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_platform_admin or current_user.role != "administrador" or current_user.empresa_id is None:
        raise ForbiddenException("Solo el administrador del tenant puede consultar el panel de procesos offline.")

    query = db.query(SyncOperation).filter(SyncOperation.empresa_id == current_user.empresa_id)
    if status:
        query = query.filter(SyncOperation.status == status)
    if operation_type:
        query = query.filter(SyncOperation.operation_type == operation_type)
    if sucursal_id is not None:
        branch = db.query(Sucursal.id).filter(
            Sucursal.id == sucursal_id,
            Sucursal.empresa_id == current_user.empresa_id,
        ).first()
        if not branch:
            raise ForbiddenException("La sucursal seleccionada no pertenece al tenant activo.")
        query = query.filter(SyncOperation.sucursal_id == sucursal_id)

    total = query.count()
    records = query.order_by(SyncOperation.created_at.desc(), SyncOperation.id.desc()).offset(offset).limit(limit).all()
    items: list[SyncAdminOperationItem] = []
    for record in records:
        user = db.query(User).filter(User.id == record.user_id).first()
        branch = db.query(Sucursal).filter(Sucursal.id == record.sucursal_id).first() if record.sucursal_id else None
        refund = db.query(ReembolsoOffline).filter(ReembolsoOffline.sync_operation_id == record.id).first()
        action_url = f"/cuenta/operaciones-pendientes?operation_uuid={record.operation_uuid}"
        notified = db.query(Notificacion.id).filter(
            Notificacion.empresa_id == record.empresa_id,
            Notificacion.user_id == record.user_id,
            Notificacion.tipo == "resultado_operacion_offline",
            Notificacion.url_accion == action_url,
        ).first() is not None
        items.append(SyncAdminOperationItem(
            operation_uuid=str(record.operation_uuid),
            operation_type=record.operation_type,
            status=record.status,
            user_id=record.user_id,
            user_name=(f"{user.name} {user.apellido or ''}".strip() if user else "Usuario eliminado"),
            user_email=user.email if user else "",
            sucursal_id=record.sucursal_id,
            sucursal_nombre=branch.name if branch else None,
            client_created_at=record.client_created_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
            reason=record.reason,
            result_type=record.result_type,
            result_id=record.result_id,
            resultado_notificado=notified,
            refund_id=refund.id if refund else None,
            refund_status=refund.estado if refund else None,
            refund_amount=float(refund.monto) if refund else None,
            refund_currency=refund.moneda if refund else None,
            refund_reason=refund.motivo if refund else None,
        ))
    return SyncAdminOperationsResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/metricas", response_model=SyncMetricasResponse, summary="Diagnóstico y métricas agregadas de sincronización offline")
async def get_sync_metrics(
    sucursal_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func

    if current_user.empresa_id is None and not current_user.is_platform_admin:
        raise ForbiddenException("La consulta de métricas de sincronización requiere pertenecer a una empresa")

    query = db.query(SyncOperation)
    if not current_user.is_platform_admin or current_user.empresa_id is not None:
        query = query.filter(SyncOperation.empresa_id == current_user.empresa_id)
    if sucursal_id is not None:
        query = query.filter(SyncOperation.sucursal_id == sucursal_id)

    total_operaciones = query.count()
    total_confirmadas = query.filter(SyncOperation.status == "confirmada").count()
    total_conflictos = query.filter(SyncOperation.status == "conflicto").count()
    total_rechazadas = query.filter(SyncOperation.status == "rechazada").count()
    total_procesando = query.filter(SyncOperation.status == "procesando").count()

    tasa_exito = round((total_confirmadas / total_operaciones * 100.0), 2) if total_operaciones > 0 else 100.0

    operaciones_rows = (
        query.with_entities(SyncOperation.operation_type, func.count(SyncOperation.id))
        .group_by(SyncOperation.operation_type)
        .all()
    )
    operaciones_por_tipo: dict[str, int] = {str(row[0]): int(row[1]) for row in operaciones_rows}

    reembolsos_query = db.query(ReembolsoOffline)
    if not current_user.is_platform_admin or current_user.empresa_id is not None:
        reembolsos_query = reembolsos_query.filter(ReembolsoOffline.empresa_id == current_user.empresa_id)
    if sucursal_id is not None:
        reembolsos_query = reembolsos_query.filter(ReembolsoOffline.sucursal_id == sucursal_id)

    reembolsos_total = reembolsos_query.count()
    monto_reembolsos = float(reembolsos_query.with_entities(func.coalesce(func.sum(ReembolsoOffline.monto), 0)).scalar())
    reembolsos_pendientes = reembolsos_query.filter(ReembolsoOffline.estado == "pendiente").count()
    reembolsos_completados = reembolsos_query.filter(ReembolsoOffline.estado == "entregado").count()

    incidentes = (
        query.filter(SyncOperation.status.in_(["conflicto", "rechazada"]))
        .order_by(SyncOperation.created_at.desc())
        .limit(10)
        .all()
    )
    conflictos_recientes = []
    for inc in incidentes:
        ref = db.query(ReembolsoOffline).filter(ReembolsoOffline.sync_operation_id == inc.id).first()
        conflictos_recientes.append(
            SyncDiagnosticoItem(
                operation_uuid=str(inc.operation_uuid),
                fecha=inc.created_at,
                operation_type=inc.operation_type,
                status=inc.status,
                sucursal_id=inc.sucursal_id,
                reason=inc.reason,
                refund_id=ref.id if ref else None,
                refund_status=ref.estado if ref else None,
            )
        )

    return SyncMetricasResponse(
        empresa_id=current_user.empresa_id,
        total_operaciones=total_operaciones,
        total_confirmadas=total_confirmadas,
        total_conflictos=total_conflictos,
        total_rechazadas=total_rechazadas,
        total_procesando=total_procesando,
        tasa_exito_porcentaje=tasa_exito,
        operaciones_por_tipo=operaciones_por_tipo,
        reembolsos_asociados={
            "total_reembolsos": reembolsos_total,
            "monto_total": monto_reembolsos,
            "pendientes": reembolsos_pendientes,
            "entregados": reembolsos_completados,
        },
        conflictos_recientes=conflictos_recientes,
    )

