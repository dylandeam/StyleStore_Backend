"""SaaS company (tenant) administration endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_platform_admin
from app.core.exceptions import BadRequestException, ForbiddenException
from app.database import get_db
from app.models.user import User
from app.schemas.empresa import (
    EmpresaConAdminResponse,
    EmpresaBrandingResponse,
    EmpresaBrandingUpdate,
    EmpresaCreate,
    EmpresaEstadoUpdate,
    EmpresaResponse,
    EmpresaPublicResponse,
    EmpresaResumenResponse,
    EmpresaSuscripcionResponse,
    EmpresaSuscripcionUpdate,
    EmpresaUpdate,
    TenantAdminResponse,
    TenantAdminUpdate,
)
from app.services.empresa_service import EmpresaService
from app.services.tenant_scope import effective_empresa_id


router = APIRouter(prefix="/empresas", tags=["Empresas SaaS"])


@router.get("/publicas/registro", response_model=list[EmpresaPublicResponse])
async def list_empresas_publicas(db: Session = Depends(get_db)):
    """Tenants activos que un cliente puede seleccionar al registrarse."""
    return EmpresaService(db).list_empresas_activas()


@router.get("/publicas/{codigo}/portal", response_model=EmpresaBrandingResponse)
async def get_portal_publico(codigo: str, db: Session = Depends(get_db)):
    """Identidad pública de un único tenant; no revela información de competidores."""
    return EmpresaService(db).get_public_branding(codigo)


@router.get("/branding/mia", response_model=EmpresaBrandingResponse)
async def get_mi_branding(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    empresa_id = effective_empresa_id(current_user)
    if not empresa_id:
        raise BadRequestException("Selecciona un tenant para consultar su identidad visual.")
    return EmpresaService.serialize_branding(EmpresaService(db).get_empresa(empresa_id))


@router.put("/branding/mia", response_model=EmpresaBrandingResponse)
async def update_mi_branding(
    request: EmpresaBrandingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_platform_admin or current_user.role != "administrador":
        raise ForbiddenException("Solo el administrador del tenant puede configurar su identidad visual.")
    if not current_user.empresa_id:
        raise BadRequestException("Tu cuenta no pertenece a un tenant.")
    return EmpresaService(db).update_branding(current_user.empresa_id, request, current_user)


@router.get("/mia", response_model=EmpresaResponse)
async def get_mi_empresa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    empresa_id = effective_empresa_id(current_user)
    if not empresa_id:
        raise BadRequestException("El usuario actual no pertenece a ninguna empresa.")
    return EmpresaService(db).get_empresa(empresa_id)


@router.get("", response_model=list[EmpresaResponse])
async def list_empresas(
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).list_empresas()


@router.get("/resumen", response_model=list[EmpresaResumenResponse])
async def list_empresas_resumen(
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).list_resumen()


@router.get("/{empresa_id}", response_model=EmpresaResumenResponse)
async def get_empresa_resumen(
    empresa_id: int,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).get_resumen(empresa_id)


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
        inactive_reason=empresa.inactive_reason,
        created_at=empresa.created_at,
        updated_at=empresa.updated_at,
        admin_user_id=admin.id,
    )


@router.patch("/{empresa_id}", response_model=EmpresaResumenResponse)
async def update_empresa(
    empresa_id: int,
    request: EmpresaUpdate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    service = EmpresaService(db)
    service.update_empresa(empresa_id, request, current_user)
    return service.get_resumen(empresa_id)


@router.put("/{empresa_id}/estado", response_model=EmpresaResumenResponse)
async def update_empresa_estado(
    empresa_id: int,
    request: EmpresaEstadoUpdate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    service = EmpresaService(db)
    service.set_active(empresa_id, request.active, current_user)
    return service.get_resumen(empresa_id)


@router.put("/{empresa_id}/administrador", response_model=TenantAdminResponse)
async def update_tenant_admin(
    empresa_id: int,
    request: TenantAdminUpdate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).update_admin(empresa_id, request, current_user)


@router.put("/{empresa_id}/suscripcion", response_model=EmpresaSuscripcionResponse)
async def update_tenant_subscription(
    empresa_id: int,
    request: EmpresaSuscripcionUpdate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
):
    raise ForbiddenException(
        "El plan del tenant solo puede cambiarse mediante el checkout PayPal del administrador empresarial."
    )
