"""Public, tenant-admin and platform-admin subscription plan endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.empresa import Empresa
from app.models.plan_suscripcion import ContratacionPlan
from app.models.user import User
from app.schemas.plan_suscripcion import (
    ContratacionCreate,
    ContratacionResponse,
    PlanResponse,
    PlanUpdate,
)
from app.services.plan_service import PlanService


router = APIRouter(prefix="/planes", tags=["Planes de Suscripción"])


def _public_empresa_id(db: Session, current_user: User | None, empresa_codigo: str | None) -> int:
    if current_user and current_user.empresa_id is not None:
        return current_user.empresa_id
    code = (empresa_codigo or "stylestore").strip().lower()
    empresa = db.query(Empresa).filter(
        Empresa.codigo == code, Empresa.active.is_(True)
    ).first()
    if not empresa:
        raise NotFoundException("Empresa no encontrada.")
    return empresa.id


@router.get("", response_model=list[PlanResponse], summary="Ver planes disponibles para clientes")
async def list_public_plans(
    empresa_codigo: str | None = Query(None),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    empresa_id = _public_empresa_id(db, current_user, empresa_codigo)
    return PlanService(db).list_plans(empresa_id, active_only=True)


@router.get("/admin", response_model=list[PlanResponse], summary="Administrar los tres planes")
async def list_admin_plans(
    empresa_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PlanService(db)
    scope_empresa_id = service.resolve_admin_scope(current_user, empresa_id)
    return service.list_plans(scope_empresa_id)


@router.put("/admin/{codigo}", response_model=PlanResponse, summary="Configurar un plan")
async def update_admin_plan(
    codigo: str,
    payload: PlanUpdate,
    empresa_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PlanService(db).update_plan(codigo, payload, current_user, empresa_id)


@router.post("/contratar", response_model=ContratacionResponse, summary="Contratar o cambiar plan")
async def contract_plan(
    payload: ContratacionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contract = PlanService(db).contract(current_user, payload.plan_codigo)
    return PlanService.serialize_contract(contract)


@router.get("/mi-contratacion", response_model=ContratacionResponse | None, summary="Ver plan contratado")
async def get_my_contract(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contract = db.query(ContratacionPlan).filter(
        ContratacionPlan.user_id == current_user.id,
        ContratacionPlan.estado == "activa",
    ).order_by(ContratacionPlan.id.desc()).first()
    return PlanService.serialize_contract(contract) if contract else None
