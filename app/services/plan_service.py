"""Business rules for the three configurable subscription plans."""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.models.empresa import Empresa
from app.models.plan_suscripcion import ContratacionPlan, PlanSuscripcion
from app.models.user import User
from app.schemas.plan_suscripcion import PLAN_CODES, PlanUpdate
from app.services.bitacora_service import BitacoraService


DEFAULT_PLANS = (
    {
        "codigo": "basico",
        "nombre": "Básico",
        "max_sucursales": 2,
        "ia_generativa": False,
        "capacidades": {
            "productos": True, "ventas": True, "reservas": True,
            "offline": True, "reportes": True, "ia_generativa": False,
        },
    },
    {
        "codigo": "profesional",
        "nombre": "Profesional",
        "max_sucursales": 10,
        "ia_generativa": True,
        "capacidades": {
            "productos": True, "ventas": True, "reservas": True,
            "offline": True, "reportes": True, "ia_generativa": True,
        },
    },
    {
        "codigo": "personalizado",
        "nombre": "Personalizado",
        "max_sucursales": None,
        "ia_generativa": False,
        "capacidades": {},
    },
)


class PlanService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def scope_key(empresa_id: int | None) -> str:
        return "global" if empresa_id is None else f"empresa:{empresa_id}"

    def seed_global_plans(self) -> None:
        for definition in DEFAULT_PLANS:
            exists = self.db.query(PlanSuscripcion).filter(
                PlanSuscripcion.scope_key == "global",
                PlanSuscripcion.codigo == definition["codigo"],
            ).first()
            if not exists:
                self.db.add(PlanSuscripcion(
                    empresa_id=None,
                    scope_key="global",
                    precio_mensual=0,
                    moneda="BOB",
                    beneficios=[],
                    estilo={},
                    active=True,
                    **definition,
                ))
        self.db.commit()

    def ensure_tenant_plans(self, empresa_id: int) -> None:
        self.seed_global_plans()
        tenant_codes = {
            row[0] for row in self.db.query(PlanSuscripcion.codigo).filter(
                PlanSuscripcion.empresa_id == empresa_id
            ).all()
        }
        globals_by_code = {
            plan.codigo: plan for plan in self.db.query(PlanSuscripcion).filter(
                PlanSuscripcion.scope_key == "global"
            ).all()
        }
        for code in PLAN_CODES - tenant_codes:
            source = globals_by_code[code]
            self.db.add(PlanSuscripcion(
                empresa_id=empresa_id,
                scope_key=self.scope_key(empresa_id),
                codigo=source.codigo,
                nombre=source.nombre,
                descripcion=source.descripcion,
                precio_mensual=source.precio_mensual,
                moneda=source.moneda,
                max_sucursales=source.max_sucursales,
                ia_generativa=source.ia_generativa,
                beneficios=list(source.beneficios or []),
                capacidades=dict(source.capacidades or {}),
                estilo=dict(source.estilo or {}),
                active=source.active,
            ))
        self.db.commit()

    def list_plans(self, empresa_id: int | None, *, active_only: bool = False):
        if empresa_id is None:
            self.seed_global_plans()
        else:
            self.ensure_tenant_plans(empresa_id)
        query = self.db.query(PlanSuscripcion).filter(
            PlanSuscripcion.scope_key == self.scope_key(empresa_id)
        )
        if active_only:
            query = query.filter(PlanSuscripcion.active.is_(True))
        order = {"basico": 0, "profesional": 1, "personalizado": 2}
        return sorted(query.all(), key=lambda item: order[item.codigo])

    def resolve_admin_scope(self, current_user: User, empresa_id: int | None) -> int | None:
        if current_user.role != "administrador":
            raise ForbiddenException("Solo los administradores pueden configurar planes.")
        if current_user.is_platform_admin:
            if empresa_id is not None and not self.db.query(Empresa.id).filter(Empresa.id == empresa_id).first():
                raise NotFoundException("Empresa no encontrada.")
            return empresa_id
        if current_user.empresa_id is None:
            raise ForbiddenException("El administrador no tiene una empresa asignada.")
        if empresa_id is not None and empresa_id != current_user.empresa_id:
            raise NotFoundException("Empresa no encontrada.")
        return current_user.empresa_id

    def update_plan(self, codigo: str, payload: PlanUpdate, current_user: User, empresa_id: int | None = None):
        code = codigo.strip().lower()
        if code not in PLAN_CODES:
            raise NotFoundException("Plan no encontrado.")
        scope_empresa_id = self.resolve_admin_scope(current_user, empresa_id)
        plans = self.list_plans(scope_empresa_id)
        plan = next(item for item in plans if item.codigo == code)
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(plan, field, value)
        if plan.codigo == "basico":
            plan.max_sucursales = min(plan.max_sucursales or 2, 2)
            plan.ia_generativa = False
            plan.capacidades = {**(plan.capacidades or {}), "ia_generativa": False}
        elif plan.codigo == "profesional":
            plan.max_sucursales = min(plan.max_sucursales or 10, 10)
            plan.ia_generativa = True
            plan.capacidades = {**(plan.capacidades or {}), "ia_generativa": True}
        self.db.commit()
        self.db.refresh(plan)
        BitacoraService.registrar(
            db=self.db,
            user=current_user,
            action=f"Actualizó el plan {plan.nombre} ({plan.codigo})",
            module="planes",
        )
        return plan

    def contract(self, current_user: User, codigo: str) -> ContratacionPlan:
        if current_user.empresa_id is None:
            raise BadRequestException("Tu cuenta no tiene una empresa asignada.")
        plan = next(
            (item for item in self.list_plans(current_user.empresa_id, active_only=True) if item.codigo == codigo),
            None,
        )
        if not plan:
            raise NotFoundException("Plan no disponible.")
        self.db.query(ContratacionPlan).filter(
            ContratacionPlan.user_id == current_user.id,
            ContratacionPlan.estado == "activa",
        ).update({ContratacionPlan.estado: "reemplazada"}, synchronize_session=False)
        contract = ContratacionPlan(
            empresa_id=current_user.empresa_id,
            user_id=current_user.id,
            plan_id=plan.id,
            estado="activa",
            precio_snapshot=plan.precio_mensual,
            moneda_snapshot=plan.moneda,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30),
        )
        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        BitacoraService.registrar(
            db=self.db, user=current_user,
            action=f"Contrató el plan {plan.nombre}", module="planes",
        )
        return contract

    def require_capability(self, current_user: User, capability: str) -> ContratacionPlan | None:
        """Require an active tenant subscription that enables a backend capability."""
        if current_user.is_platform_admin:
            return None
        if current_user.empresa_id is None:
            raise ForbiddenException("La cuenta no pertenece a una empresa contratante.")

        today = date.today()
        contract = (
            self.db.query(ContratacionPlan)
            .join(PlanSuscripcion, ContratacionPlan.plan_id == PlanSuscripcion.id)
            .filter(
                ContratacionPlan.empresa_id == current_user.empresa_id,
                ContratacionPlan.estado == "activa",
                ContratacionPlan.fecha_inicio <= today,
                (ContratacionPlan.fecha_fin.is_(None)) | (ContratacionPlan.fecha_fin >= today),
                PlanSuscripcion.active.is_(True),
            )
            .order_by(ContratacionPlan.id.desc())
            .first()
        )
        enabled = False
        if contract:
            if capability == "ia_generativa":
                enabled = bool(contract.plan.ia_generativa)
            else:
                enabled = bool((contract.plan.capacidades or {}).get(capability, False))
        if not enabled:
            raise ForbiddenException(
                "La suscripción vigente no incluye la capacidad "
                f"'{capability}'. Actualiza el plan para utilizarla."
            )
        return contract

    @staticmethod
    def serialize_contract(contract: ContratacionPlan) -> dict:
        return {
            "id": contract.id,
            "plan_codigo": contract.plan.codigo,
            "plan_nombre": contract.plan.nombre,
            "estado": contract.estado,
            "precio": contract.precio_snapshot,
            "moneda": contract.moneda_snapshot,
            "fecha_inicio": contract.fecha_inicio,
            "fecha_fin": contract.fecha_fin,
            "created_at": contract.created_at,
        }
