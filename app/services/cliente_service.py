"""
Service para gestión de Clientes (CU9).
Sin campo foto según diagrama oficial v4.
"""
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.user import User
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.services.bitacora_service import BitacoraService
from app.core.security import get_password_hash


class ClienteService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    @staticmethod
    def generar_codigo(apellido: str, nombre: str, ci: str) -> str:
        """
        Algoritmo oficial Sección 5:
        codigo = primera_letra(apellido).upper() + primera_letra(nombre).upper() + primeros_4_digitos(ci)
        """
        letra_ap = apellido.strip()[0].upper() if apellido.strip() else "C"
        letra_nom = nombre.strip()[0].upper() if nombre.strip() else "L"
        ci_digitos = re.sub(r"\D", "", ci)
        cuatro_digitos = ci_digitos[:4].ljust(4, "0")
        return f"{letra_ap}{letra_nom}{cuatro_digitos}"

    def _sync_orphan_cliente_users(self):
        """Asegura que todos los usuarios con rol 'cliente' tengan su registro en la tabla Cliente."""
        orphan_users = (
            self.db.query(User)
            .filter(User.role == "cliente")
            .outerjoin(Cliente, Cliente.user_id == User.id)
            .filter(Cliente.codigo == None)
            .all()
        )
        if not orphan_users:
            return

        for u in orphan_users:
            base_codigo = self.generar_codigo(u.apellido or "Cliente", u.name or "C", u.ci or "1000")
            codigo = base_codigo
            counter = 1
            while self.db.query(Cliente).filter(Cliente.codigo == codigo).first():
                codigo = f"{base_codigo}-{counter}"
                counter += 1

            new_cli = Cliente(
                codigo=codigo,
                user_id=u.id,
                telefono="70000000",
                direccion="Sin dirección registrada",
            )
            self.db.add(new_cli)
        self.db.commit()

    @staticmethod
    def _sanitize_names(nombre: str | None, apellido: str | None) -> tuple[str | None, str | None]:
        """Elimina la duplicación de apellidos si el nombre ya contiene el apellido como sufijo."""
        if not nombre:
            return nombre, apellido
        n = nombre.strip()
        if not apellido:
            return n, None
        a = apellido.strip()
        if n.lower().endswith(a.lower()) and len(n) > len(a):
            n = n[:-len(a)].strip()
        return n, a

    def list_clientes(self) -> list[ClienteResponse]:
        self._sync_orphan_cliente_users()
        clientes = self.db.query(Cliente).all()
        result = []
        needs_commit = False
        for cli in clientes:
            nombre = cli.user.name if cli.user else None
            apellido = cli.user.apellido if cli.user else None
            clean_nom, clean_ap = self._sanitize_names(nombre, apellido)

            if cli.user and (cli.user.name != clean_nom or cli.user.apellido != clean_ap):
                cli.user.name = clean_nom
                cli.user.apellido = clean_ap
                self.db.add(cli.user)
                needs_commit = True

            result.append(
                ClienteResponse(
                    codigo=cli.codigo,
                    user_id=cli.user_id,
                    telefono=cli.telefono,
                    direccion=cli.direccion,
                    nombre=clean_nom,
                    apellido=clean_ap,
                    ci=cli.user.ci if cli.user else None,
                    email=cli.user.email if cli.user else None,
                    role=cli.user.role if (cli.user and cli.user.role) else "cliente",
                    created_at=cli.created_at,
                    updated_at=cli.updated_at,
                )
            )
        if needs_commit:
            self.db.commit()
        return result

    def get_cliente_by_codigo(self, codigo: str) -> ClienteResponse:
        cli = self.db.query(Cliente).filter(Cliente.codigo == codigo).first()
        if not cli:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente con código '{codigo}' no encontrado.",
            )
        nom = cli.user.name if cli.user else None
        ap = cli.user.apellido if cli.user else None
        clean_nom, clean_ap = self._sanitize_names(nom, ap)
        if cli.user and (cli.user.name != clean_nom or cli.user.apellido != clean_ap):
            cli.user.name = clean_nom
            cli.user.apellido = clean_ap
            self.db.add(cli.user)
            self.db.commit()

        return ClienteResponse(
            codigo=cli.codigo,
            user_id=cli.user_id,
            telefono=cli.telefono,
            direccion=cli.direccion,
            nombre=clean_nom,
            apellido=clean_ap,
            ci=cli.user.ci if cli.user else None,
            email=cli.user.email if cli.user else None,
            role=cli.user.role if (cli.user and cli.user.role) else "cliente",
            created_at=cli.created_at,
            updated_at=cli.updated_at,
        )

    def create_cliente(self, req: ClienteCreate, current_user: User | None = None) -> ClienteResponse:
        if self.db.query(User).filter(User.email == req.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El correo electrónico '{req.email}' ya está registrado.",
            )

        clean_nom, clean_ap = self._sanitize_names(req.nombre, req.apellido)
        base_codigo = self.generar_codigo(clean_ap or "C", clean_nom or "L", req.ci)
        codigo = base_codigo
        counter = 1
        while self.db.query(Cliente).filter(Cliente.codigo == codigo).first():
            codigo = f"{base_codigo}-{counter}"
            counter += 1

        nuevo_user = User(
            email=req.email,
            name=clean_nom or req.nombre,
            apellido=clean_ap,
            ci=req.ci,
            hashed_password=get_password_hash(req.password),
            role="cliente",
            is_active=True,
        )
        self.db.add(nuevo_user)
        self.db.flush()

        nuevo_cli = Cliente(
            codigo=codigo,
            user_id=nuevo_user.id,
            telefono=req.telefono,
            direccion=req.direccion,
        )
        self.db.add(nuevo_cli)
        self.db.commit()
        self.db.refresh(nuevo_cli)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó cliente '{codigo}' para {clean_nom} {clean_ap or ''}".strip(),
                module="clientes",
            )

        return self.get_cliente_by_codigo(codigo)

    def update_cliente(
        self, codigo: str, req: ClienteUpdate, current_user: User | None = None
    ) -> ClienteResponse:
        cli = self.db.query(Cliente).filter(Cliente.codigo == codigo).first()
        if not cli:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente '{codigo}' no encontrado.",
            )

        if req.telefono is not None:
            cli.telefono = req.telefono
        if req.direccion is not None:
            cli.direccion = req.direccion

        if cli.user:
            curr_name = req.nombre if req.nombre is not None else cli.user.name
            curr_ap = req.apellido if req.apellido is not None else cli.user.apellido
            clean_nom, clean_ap = self._sanitize_names(curr_name, curr_ap)
            cli.user.name = clean_nom
            cli.user.apellido = clean_ap
            if req.ci is not None:
                cli.user.ci = req.ci

        self.db.commit()
        self.db.refresh(cli)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó datos del cliente '{codigo}'",
                module="clientes",
            )

        return self.get_cliente_by_codigo(codigo)

    def delete_cliente(self, codigo: str, current_user: User | None = None) -> dict:
        cli = self.db.query(Cliente).filter(Cliente.codigo == codigo).first()
        if not cli:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente '{codigo}' no encontrado.",
            )

        user_id = cli.user_id
        self.db.delete(cli)
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = False

        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó cliente '{codigo}'",
                module="clientes",
            )

        return {"message": f"Cliente '{codigo}' eliminado exitosamente."}
