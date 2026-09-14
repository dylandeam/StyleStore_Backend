"""
Service para gestión de Proveedores (CU16 / v5 Sección 10).
Conforme a Especificación StyleStore v5:
Con campo CI obligatorio y multiasociaciones independientes (Categorias, Temporadas, Colecciones).
Algoritmo de generación de código: PR-[2 letras nombre][2 letras apellido]-[ultimos 4 digitos CI].
"""
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.proveedor import Proveedor
from app.models.categoria import Categoria
from app.models.temporada import Temporada
from app.models.coleccion import Coleccion
from app.models.user import User
from app.schemas.proveedor import ProveedorCreate, ProveedorUpdate, ProveedorResponse
from app.services.bitacora_service import BitacoraService


class ProveedorService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    def _generar_codigo_v5(self, nombre: str, apellido: str, ci: str) -> str:
        """Algoritmo oficial v5: PR-[2 letras nombre][2 letras apellido]-[ultimos 4 digitos CI]."""
        clean_nom = re.sub(r'[^a-zA-Z]', '', nombre).upper()
        clean_ape = re.sub(r'[^a-zA-Z]', '', apellido).upper()
        nom_part = (clean_nom[:2] if len(clean_nom) >= 2 else (clean_nom + "X")[:2])
        ape_part = (clean_ape[:2] if len(clean_ape) >= 2 else (clean_ape + "X")[:2])
        clean_ci = re.sub(r'[^0-9a-zA-Z]', '', ci)
        ci_part = clean_ci[-4:] if len(clean_ci) >= 4 else clean_ci.zfill(4)

        base_code = f"PR-{nom_part}{ape_part}-{ci_part}"
        candidate = base_code
        counter = 1
        while self.db.query(Proveedor).filter(Proveedor.codigo == candidate).first():
            counter += 1
            candidate = f"{base_code}-{counter}"
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

        clean_ci = req.ci.strip() if (req.ci and req.ci.strip()) else None
        if clean_ci and self.db.query(Proveedor).filter(Proveedor.ci == clean_ci).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un proveedor con el CI '{clean_ci}'.",
            )

        if req.codigo and req.codigo.strip():
            codigo = req.codigo.strip()
        elif clean_ci:
            codigo = self._generar_codigo_v5(req.nombre, req.apellido, clean_ci)
        else:
            count = self.db.query(Proveedor).count()
            codigo = f"PROV-{count + 1:04d}"
            while self.db.query(Proveedor).filter(Proveedor.codigo == codigo).first():
                count += 1
                codigo = f"PROV-{count + 1:04d}"

        p = Proveedor(
            codigo=codigo,
            ci=clean_ci,
            nombre=req.nombre.strip(),
            apellido=req.apellido.strip(),
            email=req.email,
            telefono=req.telefono.strip(),
        )

        # Multiasociaciones independientes
        if req.categoria_ids:
            cats = self.db.query(Categoria).filter(Categoria.id.in_(req.categoria_ids)).all()
            p.categorias = cats

        if req.temporada_ids:
            temps = self.db.query(Temporada).filter(Temporada.id.in_(req.temporada_ids)).all()
            p.temporadas = temps

        if req.coleccion_ids:
            cols = self.db.query(Coleccion).filter(Coleccion.id.in_(req.coleccion_ids)).all()
            p.colecciones = cols

        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó proveedor '{p.codigo}' - {p.nombre} {p.apellido} (CI: {p.ci})",
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

        if req.email and req.email != p.email:
            if self.db.query(Proveedor).filter(Proveedor.email == req.email, Proveedor.codigo != codigo).first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe otro proveedor con el correo electrónico '{req.email}'.",
                )
            p.email = req.email

        if req.ci and req.ci.strip() != p.ci:
            clean_ci = req.ci.strip()
            if self.db.query(Proveedor).filter(Proveedor.ci == clean_ci, Proveedor.codigo != codigo).first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe otro proveedor con el CI '{clean_ci}'.",
                )
            p.ci = clean_ci

        if req.nombre is not None:
            p.nombre = req.nombre.strip()
        if req.apellido is not None:
            p.apellido = req.apellido.strip()
        if req.telefono is not None:
            p.telefono = req.telefono.strip()

        if req.categoria_ids is not None:
            cats = self.db.query(Categoria).filter(Categoria.id.in_(req.categoria_ids)).all()
            p.categorias = cats

        if req.temporada_ids is not None:
            temps = self.db.query(Temporada).filter(Temporada.id.in_(req.temporada_ids)).all()
            p.temporadas = temps

        if req.coleccion_ids is not None:
            cols = self.db.query(Coleccion).filter(Coleccion.id.in_(req.coleccion_ids)).all()
            p.colecciones = cols

        self.db.commit()
        self.db.refresh(p)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó proveedor '{p.codigo}' - {p.nombre} {p.apellido}",
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

        self.db.delete(p)
        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó proveedor '{codigo}'",
                module="proveedores",
            )

        return {"message": f"Proveedor con código '{codigo}' eliminado exitosamente."}
