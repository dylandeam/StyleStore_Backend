"""
Sucursal Service for Branch CRUD and business logic.
"""
from sqlalchemy.orm import Session

from app.models.sucursal import Sucursal
from app.models.user import User
from app.schemas.sucursal import SucursalCreate, SucursalUpdate
from app.core.exceptions import NotFoundException, ConflictException
from app.services.bitacora_service import BitacoraService


class SucursalService:
    """Service for managing Store Branches."""

    def __init__(self, db: Session):
        self.db = db

    def list_sucursales(self, active_only: bool = False) -> list[Sucursal]:
        """List all branches or only active ones."""
        query = self.db.query(Sucursal)
        if active_only:
            query = query.filter(Sucursal.active == True)
        return query.order_by(Sucursal.name).all()

    def get_sucursal_by_id(self, sucursal_id: int) -> Sucursal:
        """Get branch by ID."""
        sucursal = self.db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
        if not sucursal:
            raise NotFoundException(f"No se encontró la sucursal con ID {sucursal_id}.")
        return sucursal

    def create_sucursal(self, data: SucursalCreate, current_user: User) -> Sucursal:
        """Create a new branch."""
        existing = self.db.query(Sucursal).filter(Sucursal.name.ilike(data.name)).first()
        if existing:
            raise ConflictException(f"Ya existe una sucursal con el nombre '{data.name}'.")

        sucursal = Sucursal(
            name=data.name,
            city=data.city,
            address=data.address,
            phone=data.phone,
            active=data.active,
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
        sucursal = self.get_sucursal_by_id(sucursal_id)

        if data.name is not None and data.name.lower() != sucursal.name.lower():
            existing = self.db.query(Sucursal).filter(Sucursal.name.ilike(data.name)).first()
            if existing and existing.id != sucursal_id:
                raise ConflictException(f"Ya existe otra sucursal con el nombre '{data.name}'.")
            sucursal.name = data.name

        if data.city is not None:
            sucursal.city = data.city
        if data.address is not None:
            sucursal.address = data.address
        if data.phone is not None:
            sucursal.phone = data.phone
        if data.active is not None:
            sucursal.active = data.active

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
        sucursal = self.get_sucursal_by_id(sucursal_id)
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
