"""
Sucursal Service for Branch CRUD and business logic.
"""
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.sucursal import Sucursal
from app.models.user import User
from app.schemas.sucursal import SucursalCreate, SucursalUpdate
from app.core.exceptions import NotFoundException, ConflictException
from app.services.bitacora_service import BitacoraService
from app.services.plan_service import PlanService


class SucursalService:
    """Service for managing Store Branches."""

    def __init__(self, db: Session):
        self.db = db

    def list_sucursales(
        self,
        active_only: bool = False,
        empresa_id: int | None = None,
        include_all_empresas: bool = False,
    ) -> list[Sucursal]:
        """List all branches or only active ones."""
        query = self.db.query(Sucursal)
        if not include_all_empresas and empresa_id is not None:
            query = query.filter(Sucursal.empresa_id == empresa_id)
        if active_only:
            query = query.filter(Sucursal.active == True)
        return query.order_by(Sucursal.name).all()

    def get_sucursal_by_id(
        self,
        sucursal_id: int,
        empresa_id: int | None = None,
        include_all_empresas: bool = False,
    ) -> Sucursal:
        """Get branch by ID."""
        query = self.db.query(Sucursal).filter(Sucursal.id == sucursal_id)
        if not include_all_empresas and empresa_id is not None:
            query = query.filter(Sucursal.empresa_id == empresa_id)
        sucursal = query.first()
        if not sucursal:
            raise NotFoundException(f"No se encontró la sucursal con ID {sucursal_id}.")
        return sucursal

    def create_sucursal(self, data: SucursalCreate, current_user: User) -> Sucursal:
        """Create a new branch."""
        if current_user.empresa_id is None:
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException("El usuario no tiene una empresa asignada.")
        PlanService(self.db).require_branch_capacity(current_user)
        existing = self.db.query(Sucursal).filter(
            Sucursal.empresa_id == current_user.empresa_id,
            Sucursal.name.ilike(data.name),
        ).first()
        if existing:
            raise ConflictException(f"Ya existe una sucursal con el nombre '{data.name}'.")

        data_maps = getattr(data, "maps_url", None)
        maps_url = data_maps.strip() if isinstance(data_maps, str) and data_maps.strip() else None
        lat = Decimal(str(data.latitud)) if data.latitud is not None else None
        lon = Decimal(str(data.longitud)) if data.longitud is not None else None
        if (lat is None or lon is None) and maps_url:
            from app.core.geo import extraer_coordenadas_de_url
            plat, plon = extraer_coordenadas_de_url(maps_url)
            if plat is not None and plon is not None:
                lat, lon = Decimal(str(plat)), Decimal(str(plon))

        sucursal = Sucursal(
            empresa_id=current_user.empresa_id,
            name=data.name,
            city=data.city,
            address=data.address,
            phone=data.phone,
            maps_url=maps_url,
            latitud=lat,
            longitud=lon,
            active=data.active,
            hora_apertura=data.hora_apertura,
            hora_cierre=data.hora_cierre,
        )
        self.db.add(sucursal)
        self.db.commit()
        self.db.refresh(sucursal)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Creó la sucursal '{sucursal.name}' en '{sucursal.city}'",
            module="sucursales",
        )
        return sucursal

    def update_sucursal(
        self, sucursal_id: int, data: SucursalUpdate, current_user: User
    ) -> Sucursal:
        """Update branch information."""
        sucursal = self.get_sucursal_by_id(
            sucursal_id,
            empresa_id=current_user.empresa_id,
            include_all_empresas=current_user.is_platform_admin,
        )

        if data.name is not None and data.name.lower() != sucursal.name.lower():
            existing = self.db.query(Sucursal).filter(
                Sucursal.empresa_id == sucursal.empresa_id,
                Sucursal.name.ilike(data.name),
            ).first()
            if existing and existing.id != sucursal_id:
                raise ConflictException(f"Ya existe otra sucursal con el nombre '{data.name}'.")
            sucursal.name = data.name

        if data.city is not None:
            sucursal.city = data.city
        if data.address is not None:
            sucursal.address = data.address
        if data.phone is not None:
            sucursal.phone = data.phone
        if data.active is True and not sucursal.active:
            PlanService(self.db).require_branch_capacity(current_user)
        if data.active is not None:
            sucursal.active = data.active
        nueva_apertura = data.hora_apertura or sucursal.hora_apertura
        nuevo_cierre = data.hora_cierre or sucursal.hora_cierre
        if nueva_apertura >= nuevo_cierre:
            from app.core.exceptions import BadRequestException
            raise BadRequestException("La hora de apertura debe ser anterior a la hora de cierre.")
        sucursal.hora_apertura = nueva_apertura
        sucursal.hora_cierre = nuevo_cierre

        if hasattr(data, "maps_url") and data.maps_url is not None:
            sucursal.maps_url = data.maps_url.strip() if data.maps_url else None
            if sucursal.maps_url:
                from app.core.geo import extraer_coordenadas_de_url
                plat, plon = extraer_coordenadas_de_url(sucursal.maps_url)
                if plat is not None and plon is not None:
                    sucursal.latitud = Decimal(str(plat))
                    sucursal.longitud = Decimal(str(plon))
        if hasattr(data, "latitud") and data.latitud is not None:
            sucursal.latitud = Decimal(str(data.latitud))
        if hasattr(data, "longitud") and data.longitud is not None:
            sucursal.longitud = Decimal(str(data.longitud))

        self.db.commit()
        self.db.refresh(sucursal)

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó la sucursal '{sucursal.name}'",
            module="sucursales",
        )
        return sucursal

    def delete_sucursal(self, sucursal_id: int, current_user: User) -> dict:
        """Delete branch."""
        sucursal = self.get_sucursal_by_id(
            sucursal_id,
            empresa_id=current_user.empresa_id,
            include_all_empresas=current_user.is_platform_admin,
        )
        name = sucursal.name

        self.db.delete(sucursal)
        self.db.commit()

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Eliminó la sucursal '{name}'",
            module="sucursales",
        )
        return {"message": f"Sucursal '{name}' eliminada correctamente."}
