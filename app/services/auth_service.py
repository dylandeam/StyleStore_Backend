"""
Authentication service — business logic for register, login, logout.
"""
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.models.user import User
from app.models.empresa import Empresa
from app.models.user_empresa import UserEmpresa
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth import RegisterRequest, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import (
    BadRequestException,
    CredentialsException,
    UserAlreadyExistsException,
    InvalidTokenException,
)


from app.services.bitacora_service import BitacoraService
from app.services.plan_service import PlanService


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, db: Session):
        self.db = db

    def register(self, request: RegisterRequest) -> User:
        """
        Register a new client user.
        """
        from app.models.empresa import Empresa
        from app.models.user_empresa import UserEmpresa

        requested_codes = request.empresa_codigos or (
            [request.empresa_codigo.strip().lower()] if request.empresa_codigo else []
        )
        empresas = []
        if requested_codes:
            empresas = self.db.query(Empresa).filter(
                Empresa.codigo.in_(requested_codes), Empresa.active.is_(True)
            ).all()
            found_codes = {item.codigo for item in empresas}
            missing = [code for code in requested_codes if code not in found_codes]
            if missing:
                raise BadRequestException(
                    "Estas empresas no existen o están inactivas: " + ", ".join(missing)
                )
            empresas.sort(key=lambda item: requested_codes.index(item.codigo))
            empresa = empresas[0]
        else:
            empresa = self.db.query(Empresa).filter(Empresa.codigo == "stylestore", Empresa.active == True).first()
            if not empresa and self.db.query(Empresa).filter(Empresa.active == True).count() == 0:
                empresa = Empresa(codigo="stylestore", nombre="StyleStore", active=True)
                self.db.add(empresa)
                self.db.flush()
            elif not empresa:
                raise BadRequestException("Debe seleccionar al menos una empresa para registrarse.")
            empresas = [empresa]

        # Check if user already exists by email
        existing_user = (
            self.db.query(User).filter(User.email == request.email).first()
        )
        if existing_user:
            raise UserAlreadyExistsException("Ya existe un usuario registrado con este correo electrónico.")

        # Check CI uniqueness if provided
        ci_val = request.ci.strip() if request.ci and request.ci.strip() else None
        if ci_val:
            existing_ci = self.db.query(User).filter(User.ci == ci_val).first()
            if existing_ci:
                raise UserAlreadyExistsException("Ya existe un usuario registrado con este carnet de identidad (CI).")

        # Resolve role_id for 'cliente'
        from app.models.role import Role
        role_cliente = self.db.query(Role).filter(Role.nombre.ilike("cliente")).first()
        role_id_val = role_cliente.id if role_cliente else None

        # Sanitize name and apellido to prevent duplicate surnames (e.g. 'Lupita Cardozo Mendez' + 'Cardozo Mendez')
        raw_name = request.name.strip() if request.name else ""
        raw_apellido = request.apellido.strip() if request.apellido else ""

        if raw_apellido:
            # If name ends with apellido, strip it to leave only first name(s)
            if raw_name.lower().endswith(raw_apellido.lower()) and len(raw_name) > len(raw_apellido):
                clean_name = raw_name[:-len(raw_apellido)].strip()
                clean_apellido = raw_apellido
            elif raw_name.lower() == raw_apellido.lower():
                clean_name = raw_name
                clean_apellido = None
            else:
                clean_name = raw_name
                clean_apellido = raw_apellido
        else:
            clean_name = raw_name
            clean_apellido = None

        # Create new user with default client role (CU9 / v7 Punto 1)
        user = User(
            empresa_id=empresa.id,
            email=request.email,
            name=clean_name,
            apellido=clean_apellido,
            ci=ci_val,
            telefono=request.telefono.strip() if request.telefono else None,
            direccion=request.direccion.strip() if request.direccion else None,
            foto=request.foto.strip() if request.foto else None,
            hashed_password=hash_password(request.password),
            role="cliente",
            role_id=role_id_val,
        )
        self.db.add(user)
        self.db.flush()
        for tenant in empresas:
            self.db.add(UserEmpresa(user_id=user.id, empresa_id=tenant.id, active=True))
        self.db.commit()
        self.db.refresh(user)

        # Create corresponding Cliente record (CU9)
        from app.models.cliente import Cliente
        letra_nom = clean_name[0].upper() if clean_name else "C"
        codigo = f"CL{letra_nom}{user.id:04d}"
        # Ensure unique codigo
        c = 1
        base_codigo = codigo
        while self.db.query(Cliente).filter(Cliente.codigo == codigo).first():
            codigo = f"{base_codigo}-{c}"
            c += 1

        cliente_telefono = request.telefono.strip() if request.telefono and request.telefono.strip() else "70000000"
        cliente_direccion = request.direccion.strip() if request.direccion and request.direccion.strip() else "Sin dirección registrada"

        cliente = Cliente(
            codigo=codigo,
            user_id=user.id,
            telefono=cliente_telefono,
            direccion=cliente_direccion,
        )
        self.db.add(cliente)
        self.db.commit()

        # Log registration in bitacora
        BitacoraService.registrar(
            db=self.db,
            user=user,
            action="Registró un nuevo usuario",
            module="auth",
        )

        return user

    def login(self, email: str, password: str, empresa_codigo: str | None = None) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.
        """
        # Find user by email
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            BitacoraService.registrar(
                db=self.db,
                user=email,
                action="Intento fallido de inicio de sesión (correo no registrado)",
                module="auth",
            )
            raise CredentialsException(detail="Correo o contraseña incorrectos")

        # Verify password
        if not verify_password(password, user.hashed_password):
            BitacoraService.registrar(
                db=self.db,
                user=user,
                action="Intento fallido de inicio de sesión (contraseña incorrecta)",
                module="auth",
            )
            raise CredentialsException(detail="Correo o contraseña incorrectos")

        # Check if user is active
        if not user.is_active:
            raise CredentialsException(detail="La cuenta de usuario está desactivada")

        selected_empresa_id = user.empresa_id
        selected_empresa = None
        if empresa_codigo:
            selected_empresa = self.db.query(Empresa).filter(
                Empresa.codigo == empresa_codigo.strip().lower()
            ).first()
            if not selected_empresa:
                raise CredentialsException(detail="El tenant seleccionado no existe")
            if not user.is_platform_admin:
                membership = self.db.query(UserEmpresa.id).filter(
                    UserEmpresa.user_id == user.id,
                    UserEmpresa.empresa_id == selected_empresa.id,
                    UserEmpresa.active.is_(True),
                ).first()
                if not membership:
                    raise CredentialsException(
                        detail="Tu cuenta no está registrada en el tenant seleccionado"
                    )
            selected_empresa_id = selected_empresa.id

        if not user.is_platform_admin and selected_empresa_id is not None:
            empresa, _ = PlanService(self.db).reconcile_tenant_access(selected_empresa_id)
            if not empresa.active:
                if empresa.inactive_reason == "subscription_expired" and user.role == "administrador":
                    pass
                elif empresa.inactive_reason == "subscription_expired":
                    raise CredentialsException(
                        detail="La suscripción de la empresa venció. Contacta al administrador para renovarla."
                    )
                else:
                    raise CredentialsException(detail="La empresa se encuentra suspendida")

        # Generate tokens
        token_data = {
            "sub": str(user.id),
            "role": user.role,
            "email": user.email,
            "empresa_id": selected_empresa_id,
        }
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "empresa_id": selected_empresa_id}
        )

        # Log successful login in bitacora
        BitacoraService.registrar(
            db=self.db,
            user=user,
            action="Inició sesión",
            module="auth",
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def list_tenants(self, current_user: User) -> list[dict]:
        memberships = (
            self.db.query(UserEmpresa)
            .join(Empresa, UserEmpresa.empresa_id == Empresa.id)
            .filter(UserEmpresa.user_id == current_user.id, UserEmpresa.active.is_(True))
            .order_by(Empresa.nombre)
            .all()
        )
        return [
            {
                "id": membership.empresa.id,
                "codigo": membership.empresa.codigo,
                "nombre": membership.empresa.nombre,
                "active": membership.empresa.active,
                "is_current": membership.empresa_id == current_user.empresa_id,
            }
            for membership in memberships
        ]

    def select_tenant(self, current_user: User, empresa_id: int) -> TokenResponse:
        membership = self.db.query(UserEmpresa).filter(
            UserEmpresa.user_id == current_user.id,
            UserEmpresa.empresa_id == empresa_id,
            UserEmpresa.active.is_(True),
        ).first()
        if not membership:
            raise BadRequestException("Tu cuenta no está registrada en esa empresa.")
        empresa = self.db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa or not empresa.active:
            raise BadRequestException("La empresa seleccionada no está disponible actualmente.")
        set_committed_value(current_user, "empresa_id", empresa_id)
        token_data = {
            "sub": str(current_user.id),
            "role": current_user.role,
            "email": current_user.email,
            "empresa_id": empresa_id,
        }
        BitacoraService.registrar(
            self.db, current_user,
            f"Cambió su contexto activo al tenant '{empresa.nombre}'", "auth",
        )
        return TokenResponse(
            access_token=create_access_token(data=token_data),
            refresh_token=create_refresh_token(
                data={"sub": str(current_user.id), "empresa_id": empresa_id}
            ),
            token_type="bearer",
        )

    def logout(self, token: str, current_user: User | None = None) -> None:
        """
        Revoke a token by adding it to the blacklist.
        """
        # Check if token is already blacklisted
        existing = (
            self.db.query(TokenBlacklist)
            .filter(TokenBlacklist.token == token)
            .first()
        )
        if not existing:
            blacklisted = TokenBlacklist(token=token)
            self.db.add(blacklisted)
            self.db.commit()

        if current_user:
            BitacoraService.registrar(
                db=self.db,
                user=current_user,
                action="Cerró sesión",
                module="auth",
            )

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if a token has been revoked."""
        return (
            self.db.query(TokenBlacklist)
            .filter(TokenBlacklist.token == token)
            .first()
            is not None
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate a new access token using a valid refresh token.
        
        Args:
            refresh_token: A valid refresh token.
        
        Returns:
            New TokenResponse with fresh access token.
        
        Raises:
            InvalidTokenException: If refresh token is invalid or blacklisted.
        """
        # Check if token is blacklisted
        if self.is_token_blacklisted(refresh_token):
            raise InvalidTokenException()

        # Decode the refresh token
        payload = decode_token(refresh_token)
        if payload is None:
            raise InvalidTokenException()

        if payload.get("type") != "refresh":
            raise InvalidTokenException(detail="Invalid token type")

        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenException()

        user = self.db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
        if not user:
            raise InvalidTokenException()

        token_empresa_id = payload.get("empresa_id")
        if token_empresa_id is not None and not user.is_platform_admin:
            empresa_id = int(token_empresa_id)
            if empresa_id != user.empresa_id:
                membership = self.db.query(UserEmpresa.id).filter(
                    UserEmpresa.user_id == user.id,
                    UserEmpresa.empresa_id == empresa_id,
                    UserEmpresa.active.is_(True),
                ).first()
                if not membership:
                    raise InvalidTokenException(detail="El tenant del token ya no está disponible")
            set_committed_value(user, "empresa_id", empresa_id)

        if not user.is_platform_admin and user.empresa_id is not None:
            empresa, _ = PlanService(self.db).reconcile_tenant_access(user.empresa_id)
            if not empresa.active and not (
                empresa.inactive_reason == "subscription_expired" and user.role == "administrador"
            ):
                raise InvalidTokenException(
                    detail=(
                        "La suscripción de la empresa venció. Contacta al administrador para renovarla."
                        if empresa.inactive_reason == "subscription_expired"
                        else "La empresa se encuentra suspendida"
                    )
                )

        # Generate a new access token from current server-side identity data.
        token_data = {
            "sub": user_id,
            "role": user.role,
            "email": user.email,
            "empresa_id": user.empresa_id,
        }
        new_access_token = create_access_token(data=token_data)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
