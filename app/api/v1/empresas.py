"""SaaS company (tenant) administration endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_platform_admin
from app.database import get_db
from app.models.user import User
from app.schemas.empresa import EmpresaConAdminResponse, EmpresaCreate, EmpresaResponse
from app.services.empresa_service import EmpresaService


router = APIRouter(prefix="/empresas", tags=["Empresas SaaS"])


@router.get("/mia", response_model=EmpresaResponse)
async def get_mi_empresa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return EmpresaService(db).get_empresa(current_user.empresa_id)


@router.get("", response_model=list[EmpresaResponse])
async def list_empresas(
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).list_empresas()


@router.post("", response_model=EmpresaConAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_empresa(
    request: EmpresaCreate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    empresa, admin = EmpresaService(db).create_empresa(request, current_user)
    return EmpresaConAdminResponse(
        id=empresa.id,
        codigo=empresa.codigo,
        nombre=empresa.nombre,
        active=empresa.active,
        created_at=empresa.created_at,
        updated_at=empresa.updated_at,
        admin_user_id=admin.id,
    )
