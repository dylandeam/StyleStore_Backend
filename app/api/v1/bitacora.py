"""
Bitacora (Audit Log) endpoints (CU6).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import require_permission
from app.schemas.bitacora import BitacoraPageResponse
from app.services.bitacora_service import BitacoraService

router = APIRouter(prefix="/bitacora", tags=["Bitacora / Auditoria"])


@router.get(
    "",
    response_model=BitacoraPageResponse,
    summary="Visualizar bitácora",
    description="Obtiene los registros de auditoría del sistema, ordenados descendentemente por fecha.",
)
async def list_bitacora(
    user: str | None = Query(None, description="Filtrar por nombre o correo de usuario"),
    from_date: datetime | None = Query(None, alias="from", description="Fecha inicial"),
    to_date: datetime | None = Query(None, alias="to", description="Fecha final"),
    module: str | None = Query(None, description="Módulo filtrado"),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Cantidad de registros por página"),
    current_user: User = Depends(require_permission("bitacora.ver")),
    db: Session = Depends(get_db),
):
    """Listar registros de auditoría filtrados y paginados."""
    service = BitacoraService()
    return service.list_logs(
        db=db,
        user_query=user,
        from_date=from_date,
        to_date=to_date,
        module=module,
        page=page,
        size=size,
    )
