"""Business logic for company tenant administration."""
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.role import Role
from app.models.user import User
from app.schemas.empresa import EmpresaCreate
from app.services.bitacora_service import BitacoraService


class EmpresaService:
    def __init__(self, db: Session):
        self.db = db

    def list_empresas(self) -> list[Empresa]:
        return self.db.query(Empresa).order_by(Empresa.nombre).all()

    def get_empresa(self, empresa_id: int) -> Empresa:
        empresa = self.db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            raise NotFoundException("Empresa no encontrada.")
        return empresa

    def create_empresa(self, data: EmpresaCreate, current_user: User) -> tuple[Empresa, User]:
        if self.db.query(Empresa).filter((Empresa.codigo == data.codigo) | (Empresa.nombre.ilike(data.nombre.strip()))).first():
            raise ConflictException("Ya existe una empresa con ese código o nombre.")
        if self.db.query(User).filter(User.email == data.admin_email).first():
            raise ConflictException("Ya existe un usuario con el correo del administrador indicado.")

        role = self.db.query(Role).filter(Role.nombre.ilike("administrador")).first()
        try:
            empresa = Empresa(codigo=data.codigo, nombre=data.nombre.strip(), active=True)
            self.db.add(empresa)
            self.db.flush()

            admin = User(
                empresa_id=empresa.id,
                email=data.admin_email,
                name=data.admin_name.strip(),
                hashed_password=hash_password(data.admin_password),
                role="administrador",
                role_id=role.id if role else None,
                is_platform_admin=False,
                is_active=True,
            )
            self.db.add(admin)
            self.db.commit()
            self.db.refresh(empresa)
            self.db.refresh(admin)
        except Exception:
            self.db.rollback()
            raise

        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Registró la empresa '{empresa.nombre}' ({empresa.codigo})",
            module="empresas",
        )
        return empresa, admin
