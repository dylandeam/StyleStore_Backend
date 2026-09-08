"""
Endpoints para subida de imágenes y archivos estáticos (Productos y Empleados).
Persistencia dual: en disco para velocidad y en base de datos para sobrevivir
redeployments y reinicios de contenedores en la nube (Railway).
"""
import os
import uuid
import pathlib
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.uploaded_file import UploadedFile
from app.api.deps import get_current_user

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FOLDERS = {"productos", "empleados"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post(
    "",
    summary="Subir imagen de producto o empleado desde almacenamiento local",
    description="Permite subir un archivo PNG o JPG para asociarlo a un producto o empleado.",
)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Query("productos", description="Carpeta destino: 'productos' o 'empleados'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if folder not in ALLOWED_FOLDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Carpeta inválida. Solo se permite subir a: {', '.join(ALLOWED_FOLDERS)}",
        )

    # Validar extensión
    ext = pathlib.Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no permitido. Solo se admiten imágenes JPG, PNG o WEBP (recibido: '{ext}').",
        )

    # Leer contenido para validar tamaño
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen excede el tamaño máximo permitido de 5 MB.",
        )

    # Asegurar directorio de destino en disco
    dest_dir = os.path.join(os.getcwd(), "uploads", folder)
    os.makedirs(dest_dir, exist_ok=True)

    # Generar nombre único
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    dest_path = os.path.join(dest_dir, safe_name)

    # 1. Guardar en disco para acceso estático rápido
    try:
        with open(dest_path, "wb") as f:
            f.write(content)
    except Exception as e:
        print(f"Warning writing upload to disk: {e}")

    # 2. Guardar en base de datos para persistencia inmutable en Railway
    try:
        file_record = UploadedFile(
            filename=safe_name,
            folder=folder,
            content_type=file.content_type or "image/jpeg",
            file_size=len(content),
            data=content,
        )
        db.add(file_record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning saving upload to database: {e}")

    url_path = f"/uploads/{folder}/{safe_name}"

    return {
        "url": url_path,
        "filename": safe_name,
        "size": len(content),
        "content_type": file.content_type,
    }
