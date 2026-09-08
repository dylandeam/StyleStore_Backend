"""
Service para gestión de Empleados (CU8).
"""
import re
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.empleado import Empleado
from app.models.user import User
from app.models.sucursal import Sucursal
from app.schemas.empleado import EmpleadoCreate, EmpleadoUpdate, EmpleadoResponse
from app.services.bitacora_service import BitacoraService
from app.core.security import get_password_hash


class EmpleadoService:
    def __init__(self, db: Session):
        self.db = db
        self.bitacora = BitacoraService(db)

    @staticmethod
    def generar_codigo(apellido: str, nombre: str, ci: str) -> str:
        """
        Algoritmo oficial Sección 5:
        codigo = primera_letra(apellido).upper() + primera_letra(nombre).upper() + primeros_4_digitos(ci)
        """
        letra_ap = apellido.strip()[0].upper() if apellido.strip() else "X"
        letra_nom = nombre.strip()[0].upper() if nombre.strip() else "X"
        ci_digitos = re.sub(r"\D", "", ci)
        cuatro_digitos = ci_digitos[:4].ljust(4, "0")
        return f"{letra_ap}{letra_nom}{cuatro_digitos}"

    def list_empleados(self) -> list[EmpleadoResponse]:
        empleados = self.db.query(Empleado).all()
        result = []
        for emp in empleados:
            result.append(
                EmpleadoResponse(
                    codigo=emp.codigo,
                    user_id=emp.user_id,
                    sucursal_id=emp.sucursal_id,
                    edad=emp.edad,
                    sueldo=emp.sueldo,
                    telefono=emp.telefono,
                    direccion=emp.direccion,
                    foto=emp.foto,
                    nombre=emp.user.name if emp.user else None,
                    apellido=emp.user.apellido if emp.user else None,
                    ci=emp.user.ci if emp.user else None,
                    email=emp.user.email if emp.user else None,
                    role=emp.user.role if emp.user else None,
                    sucursal_nombre=emp.sucursal.name if emp.sucursal else None,
                    created_at=emp.created_at,
                    updated_at=emp.updated_at,
                )
            )
        return result

    def get_empleado_by_codigo(self, codigo: str) -> EmpleadoResponse:
        emp = self.db.query(Empleado).filter(Empleado.codigo == codigo).first()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empleado con código '{codigo}' no encontrado.",
            )
        return EmpleadoResponse(
            codigo=emp.codigo,
            user_id=emp.user_id,
            sucursal_id=emp.sucursal_id,
            edad=emp.edad,
            sueldo=emp.sueldo,
            telefono=emp.telefono,
            direccion=emp.direccion,
            foto=emp.foto,
            nombre=emp.user.name if emp.user else None,
            apellido=emp.user.apellido if emp.user else None,
            ci=emp.user.ci if emp.user else None,
            email=emp.user.email if emp.user else None,
            role=emp.user.role if emp.user else None,
            sucursal_nombre=emp.sucursal.name if emp.sucursal else None,
            created_at=emp.created_at,
            updated_at=emp.updated_at,
        )

    def create_empleado(self, req: EmpleadoCreate, current_user: User | None = None) -> EmpleadoResponse:
        # Verificar email único
        if self.db.query(User).filter(User.email == req.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El correo electrónico '{req.email}' ya está registrado.",
            )

        # Verificar sucursal existente
        sucursal = self.db.query(Sucursal).filter(Sucursal.id == req.sucursal_id).first()
        if not sucursal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La sucursal con ID {req.sucursal_id} no existe.",
            )

        # Generar código
        base_codigo = self.generar_codigo(req.apellido, req.nombre, req.ci)
        codigo = base_codigo
        counter = 1
        while self.db.query(Empleado).filter(Empleado.codigo == codigo).first():
            codigo = f"{base_codigo}-{counter}"
            counter += 1

        # Crear Usuario asociado
        nuevo_user = User(
            email=req.email,
            name=req.nombre,
            apellido=req.apellido,
            ci=req.ci,
            hashed_password=get_password_hash(req.password),
            role=req.role,
            is_active=True,
        )
        self.db.add(nuevo_user)
        self.db.flush()

        # Crear Empleado
        nuevo_emp = Empleado(
            codigo=codigo,
            user_id=nuevo_user.id,
            sucursal_id=req.sucursal_id,
            edad=req.edad,
            sueldo=req.sueldo,
            telefono=req.telefono,
            direccion=req.direccion,
            foto=req.foto,
        )
        self.db.add(nuevo_emp)
        self.db.commit()
        self.db.refresh(nuevo_emp)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Creó empleado '{codigo}' para {req.nombre} {req.apellido} en sucursal {sucursal.name}",
                module="empleados",
            )

        return self.get_empleado_by_codigo(codigo)

    def update_empleado(
        self, codigo: str, req: EmpleadoUpdate, current_user: User | None = None
    ) -> EmpleadoResponse:
        emp = self.db.query(Empleado).filter(Empleado.codigo == codigo).first()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empleado '{codigo}' no encontrado.",
            )

        if req.sucursal_id is not None:
            if not self.db.query(Sucursal).filter(Sucursal.id == req.sucursal_id).first():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Sucursal con ID {req.sucursal_id} no existe.",
                )
            emp.sucursal_id = req.sucursal_id

        if req.edad is not None:
            emp.edad = req.edad
        if req.sueldo is not None:
            emp.sueldo = req.sueldo
        if req.telefono is not None:
            emp.telefono = req.telefono
        if req.direccion is not None:
            emp.direccion = req.direccion
        if req.foto is not None:
            emp.foto = req.foto

        # Actualizar datos de User
        if emp.user:
            if req.nombre is not None:
                emp.user.name = req.nombre
            if req.apellido is not None:
                emp.user.apellido = req.apellido
            if req.ci is not None:
                emp.user.ci = req.ci

        self.db.commit()
        self.db.refresh(emp)

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Actualizó datos del empleado '{codigo}'",
                module="empleados",
            )

        return self.get_empleado_by_codigo(codigo)

    def delete_empleado(self, codigo: str, current_user: User | None = None) -> dict:
        emp = self.db.query(Empleado).filter(Empleado.codigo == codigo).first()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empleado '{codigo}' no encontrado.",
            )

        user_id = emp.user_id
        self.db.delete(emp)
        # Opcionalmente desactivar o eliminar usuario
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = False

        self.db.commit()

        if current_user:
            self.bitacora.registrar_accion(
                user_id=current_user.id,
                user_snapshot=f"{current_user.name} ({current_user.email})",
                action=f"Eliminó al empleado '{codigo}'",
                module="empleados",
            )

        return {"message": f"Empleado '{codigo}' eliminado exitosamente."}
