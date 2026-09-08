"""
Service para gestión de Proveedores (CU16).
Conforme a Especificación StyleStore v4 (Diagrama DB Oficial).
Sin campo CI según diagrama.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.proveedor import Proveedor
from app.models.user import User
from app.schemas.proveedor import ProveedorCreate, ProveedorUpdate, ProveedorResponse
from app.services.bitacora_service import BitacoraService


class ProveedorService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def _generar_codigo_siguiente(self) -> str:
        """Autogenera PROV-0001 sin requerir CI (especificación v4)."""
        count = self.db.query(Proveedor).count()
        candidate = f"PROV-{count + 1:04d}"
        while self.db.query(Proveedor).filter(Proveedor.codigo == candidate).first():
            count += 1
            candidate = f"PROV-{count + 1:04d}"
        return candidate

    def list_proveedores(self) -> list[ProveedorResponse]:
        provs = self.db.query(Proveedor).order_by(Proveedor.nombre.asc()).all()
        return [ProveedorResponse.model_validate(p) for p in provs]

    def get_proveedor_by_codigo(self, codigo: str) -> ProveedorResponse:
        p = self.db.query(Proveedor).filter(Proveedor.codigo == codigo).first()
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proveedor con código '{codigo}' no encontrado.",
            )
        return ProveedorResponse.model_validate(p)

    def create_proveedor(self, req: ProveedorCreate, current_user: User | None = None) -> ProveedorResponse:
        if self.db.query(Proveedor).filter(Proveedor.email == req.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un proveedor con el correo electrónico '{req.email}'.",
            )

        codigo = req.codigo.strip() if req.codigo and req.codigo.strip() else self._generar_codigo_siguiente()
        if self.db.query(Proveedor).filter(Proveedor.codigo == codigo).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un proveedor con el código '{codigo}'.",
            )

        p = Proveedor(
            codigo=codigo,
            nombre=req.nombre.strip(),
            apellido=req.apellido.strip(),
            email=req.email,
            telefono=req.telefono.strip(),
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó proveedor '{p.codigo}' - {p.nombre} {p.apellido}",
                module="proveedores",
            )

        return ProveedorResponse.model_validate(p)

    def update_proveedor(
        self, codigo: str, req: ProveedorUpdate, current_user: User | None = None
    ) -> ProveedorResponse:
        p = self.db.query(Proveedor).filter(Proveedor.codigo == codigo).first()
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proveedor con código '{codigo}' no encontrado.",
            )

        if req.email is not None and req.email != p.email:
            existente = self.db.query(Proveedor).filter(Proveedor.email == req.email).first()
            if existente:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe otro proveedor con el correo '{req.email}'.",
                )
            p.email = req.email

        if req.nombre is not None:
            p.nombre = req.nombre.strip()
        if req.apellido is not None:
            p.apellido = req.apellido.strip()
        if req.telefono is not None:
            p.telefono = req.telefono.strip()

        self.db.commit()
        self.db.refresh(p)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó datos del proveedor '{codigo}'",
                module="proveedores",
            )

        return ProveedorResponse.model_validate(p)

    def delete_proveedor(self, codigo: str, current_user: User | None = None) -> dict:
        p = self.db.query(Proveedor).filter(Proveedor.codigo == codigo).first()
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proveedor con código '{codigo}' no encontrado.",
            )

        nombre = f"{p.nombre} {p.apellido}"
        self.db.delete(p)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó proveedor '{codigo}' - {nombre}",
                module="proveedores",
            )

        return {"message": f"Proveedor '{codigo}' eliminado exitosamente."}
