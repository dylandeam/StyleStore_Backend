"""Business logic for company tenant administration."""
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.role import Role
from app.models.plan_suscripcion import ContratacionPlan
from app.models.sucursal import Sucursal
from app.models.user import User
from app.schemas.empresa import EmpresaCreate, EmpresaSuscripcionUpdate, EmpresaUpdate, TenantAdminUpdate
from app.services.bitacora_service import BitacoraService
from app.services.plan_service import PlanService


class EmpresaService:
    def __init__(self, db: Session):
        self.db = db

    def list_empresas(self) -> list[Empresa]:
        return self.db.query(Empresa).order_by(Empresa.nombre).all()

    def list_resumen(self) -> list[dict]:
        return [self.serialize_resumen(empresa) for empresa in self.list_empresas()]

    def get_empresa(self, empresa_id: int) -> Empresa:
        empresa = self.db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            raise NotFoundException("Empresa no encontrada.")
        return empresa

    def get_resumen(self, empresa_id: int) -> dict:
        return self.serialize_resumen(self.get_empresa(empresa_id))

    def _tenant_admin(self, empresa_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.empresa_id == empresa_id,
                User.role == "administrador",
                User.is_platform_admin.is_(False),
            )
            .order_by(User.is_active.desc(), User.id.asc())
            .first()
        )

    def _active_contract(self, empresa_id: int) -> ContratacionPlan | None:
        return (
            self.db.query(ContratacionPlan)
            .filter(ContratacionPlan.empresa_id == empresa_id)
            .order_by(
                (ContratacionPlan.estado == "activa").desc(),
                ContratacionPlan.id.desc(),
            )
            .first()
        )

    def serialize_resumen(self, empresa: Empresa) -> dict:
        empresa, _ = PlanService(self.db).reconcile_tenant_access(empresa.id)
        admin = self._tenant_admin(empresa.id)
        contract = self._active_contract(empresa.id)
        subscription = None
        if contract:
            subscription = {
                "id": contract.id,
                "plan_codigo": contract.plan.codigo,
                "plan_nombre": contract.plan.nombre,
                "estado": contract.estado,
                "estado_pago": contract.estado_pago,
                "referencia_pago": contract.referencia_pago,
                "pagado_en": contract.pagado_en,
                "precio": float(contract.precio_snapshot),
                "moneda": contract.moneda_snapshot,
                "fecha_inicio": contract.fecha_inicio,
                "fecha_fin": contract.fecha_fin,
                "max_sucursales": contract.plan.max_sucursales,
            }
        return {
            "id": empresa.id,
            "codigo": empresa.codigo,
            "nombre": empresa.nombre,
            "active": empresa.active,
            "inactive_reason": empresa.inactive_reason,
            "created_at": empresa.created_at,
            "updated_at": empresa.updated_at,
            "admin": admin,
            "suscripcion": subscription,
            "usuarios_count": self.db.query(func.count(User.id)).filter(User.empresa_id == empresa.id).scalar() or 0,
            "sucursales_count": self.db.query(func.count(Sucursal.id)).filter(Sucursal.empresa_id == empresa.id).scalar() or 0,
        }

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
        self.set_subscription(
            empresa.id,
            EmpresaSuscripcionUpdate(plan_codigo=data.plan_codigo),
            current_user,
        )
        return empresa, admin

    def update_empresa(self, empresa_id: int, data: EmpresaUpdate, current_user: User) -> Empresa:
        empresa = self.get_empresa(empresa_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return empresa
        duplicate = self.db.query(Empresa).filter(Empresa.id != empresa_id)
        if "codigo" in changes and duplicate.filter(Empresa.codigo == changes["codigo"]).first():
            raise ConflictException("Ya existe una empresa con ese código.")
        if "nombre" in changes:
            changes["nombre"] = changes["nombre"].strip()
            if duplicate.filter(Empresa.nombre.ilike(changes["nombre"])).first():
                raise ConflictException("Ya existe una empresa con ese nombre.")
        for field, value in changes.items():
            setattr(empresa, field, value)
        self.db.commit()
        self.db.refresh(empresa)
        BitacoraService.registrar(self.db, current_user, f"Actualizó el tenant '{empresa.nombre}'", "empresas")
        return empresa

    def set_active(self, empresa_id: int, active: bool, current_user: User) -> Empresa:
        empresa = self.get_empresa(empresa_id)
        if active:
            _, valid_contract = PlanService(self.db).reconcile_tenant_access(empresa_id)
            if not valid_contract:
                raise ConflictException(
                    "No se puede reactivar el tenant sin una suscripción vigente y pagada."
                )
            empresa.active = True
            empresa.inactive_reason = None
        else:
            empresa.active = False
            empresa.inactive_reason = "manual"
        self.db.commit()
        self.db.refresh(empresa)
        estado = "reactivó" if active else "suspendió"
        BitacoraService.registrar(self.db, current_user, f"{estado.capitalize()} el tenant '{empresa.nombre}'", "empresas")
        return empresa

    def update_admin(self, empresa_id: int, data: TenantAdminUpdate, current_user: User) -> User:
        empresa = self.get_empresa(empresa_id)
        admin = self._tenant_admin(empresa_id)
        if not admin:
            raise NotFoundException("El tenant no tiene un administrador asignado.")
        changes = data.model_dump(exclude_unset=True)
        if "email" in changes and changes["email"] != admin.email:
            if self.db.query(User).filter(User.email == changes["email"], User.id != admin.id).first():
                raise ConflictException("Ya existe un usuario con ese correo.")
            admin.email = changes["email"]
        if "name" in changes:
            admin.name = changes["name"].strip()
        if "password" in changes:
            admin.hashed_password = hash_password(changes["password"])
        if "is_active" in changes:
            admin.is_active = changes["is_active"]
        self.db.commit()
        self.db.refresh(admin)
        BitacoraService.registrar(self.db, current_user, f"Actualizó al administrador del tenant '{empresa.nombre}'", "empresas")
        return admin

    def set_subscription(
        self, empresa_id: int, data: EmpresaSuscripcionUpdate, current_user: User
    ) -> ContratacionPlan:
        empresa = self.get_empresa(empresa_id)
        admin = self._tenant_admin(empresa_id)
        if not admin:
            raise NotFoundException("El tenant no tiene un administrador asignado.")
        service = PlanService(self.db)
        plan = next(
            (item for item in service.list_plans(empresa_id) if item.codigo == data.plan_codigo),
            None,
        )
        if not plan:
            raise NotFoundException("Plan no encontrado.")
        start = data.fecha_inicio or date.today()
        end = data.fecha_fin or (start + timedelta(days=30))
        if end < start:
            raise ConflictException("La fecha de vencimiento no puede ser anterior al inicio.")
        if data.estado == "activa" and not data.pago_confirmado:
            raise ConflictException(
                "Una suscripción activa requiere la confirmación del pago."
            )
        self.db.query(ContratacionPlan).filter(
            ContratacionPlan.empresa_id == empresa_id,
            ContratacionPlan.estado == "activa",
        ).update({ContratacionPlan.estado: "reemplazada"}, synchronize_session=False)
        contract = ContratacionPlan(
            empresa_id=empresa_id,
            user_id=admin.id,
            plan_id=plan.id,
            estado=data.estado,
            estado_pago="pagado" if data.pago_confirmado else "pendiente",
            referencia_pago=(
                data.referencia_pago
                or (f"ADMIN-{uuid4().hex[:16].upper()}" if data.pago_confirmado else None)
            ),
            pagado_en=datetime.now(timezone.utc) if data.pago_confirmado else None,
            precio_snapshot=plan.precio_mensual,
            moneda_snapshot=plan.moneda,
            fecha_inicio=start,
            fecha_fin=end,
        )
        self.db.add(contract)
        if data.estado == "activa" and data.pago_confirmado:
            if empresa.inactive_reason in {"subscription_expired", "payment_pending"}:
                empresa.active = True
                empresa.inactive_reason = None
        elif empresa.active:
            empresa.active = False
            empresa.inactive_reason = "payment_pending"
        self.db.commit()
        self.db.refresh(contract)
        BitacoraService.registrar(
            self.db,
            current_user,
            f"Asignó el plan {plan.nombre} al tenant '{empresa.nombre}' hasta {end.isoformat()}",
            "planes",
        )
        return contract
