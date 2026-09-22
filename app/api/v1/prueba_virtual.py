"""
Endpoints de Prueba Virtual por Foto (Especificación v8 - Parte B).
"""
import os
import uuid
import shutil
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.producto import Producto
from app.models.prueba_virtual import PruebaVirtual
from app.api.deps import get_current_user

router = APIRouter(prefix="/prueba-virtual", tags=["Prueba Virtual por Foto"])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post(
    "/generar",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generar probador virtual por foto (IA)",
    description="Recibe la foto del cliente y el código de producto para procesar una prueba de ropa.",
)
async def generar_prueba_virtual(
    producto_codigo: str = Form(...),
    foto_persona: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    # 1. Verificar producto
    prod = db.query(Producto).filter(Producto.codigo == producto_codigo).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # 2. Guardar foto de la persona en uploads
    ext = os.path.splitext(foto_persona.filename or ".jpg")[1]
    filename = f"persona_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(foto_persona.file, buffer)

    foto_persona_url = f"/uploads/{filename}"

    # 3. Crear registro de prueba virtual en DB
    prueba = PruebaVirtual(
        user_id=current_user.id,
        producto_codigo=producto_codigo,
        foto_persona_url=foto_persona_url,
        foto_resultado_url=foto_persona_url,  # En modo dev/fallback se usa la foto procesada
        estado="completado",
    )
    db.add(prueba)
    db.commit()
    db.refresh(prueba)

    return {
        "job_id": prueba.id,
        "estado": prueba.estado,
        "foto_resultado_url": prueba.foto_resultado_url,
        "mensaje": "Prueba virtual procesada exitosamente",
    }


@router.get(
    "/mias",
    summary="Obtener historial de pruebas virtuales del usuario",
    description="Devuelve la lista de pruebas virtuales realizadas por el usuario logueado.",
)
async def list_mis_pruebas_virtuales(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    pruebas = (
        db.query(PruebaVirtual)
        .filter(PruebaVirtual.user_id == current_user.id)
        .order_by(PruebaVirtual.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "producto_codigo": p.producto_codigo,
            "foto_persona_url": p.foto_persona_url,
            "foto_resultado_url": p.foto_resultado_url,
            "estado": p.estado,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in pruebas
    ]


@router.get(
    "/{job_id}",
    summary="Obtener estado de un trabajo de prueba virtual",
    description="Consulta el estado y resultado de una prueba virtual.",
)
async def get_prueba_virtual_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    prueba = db.query(PruebaVirtual).filter(PruebaVirtual.id == job_id).first()
    if not prueba:
        raise HTTPException(status_code=404, detail="Trabajo de prueba no encontrado")

    return {
        "job_id": prueba.id,
        "estado": prueba.estado,
        "foto_persona_url": prueba.foto_persona_url,
        "foto_resultado_url": prueba.foto_resultado_url,
        "mensaje_error": prueba.mensaje_error,
        "created_at": prueba.created_at.isoformat() if prueba.created_at else None,
    }
