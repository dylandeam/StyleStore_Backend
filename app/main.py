"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from app.config import settings
from app.api.v1.router import api_v1_router
from app.middleware.error_handler import register_error_handlers
from app.init_db import init_db


async def _notification_campaign_worker(stop_event: asyncio.Event) -> None:
    """Despacha campañas vencidas sin perder la programación al reiniciar Railway."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
            continue
        except asyncio.TimeoutError:
            pass
        try:
            def run_due_campaigns() -> None:
                from app.database import SessionLocal
                from app.models.notificacion import CampanaNotificacion
                from app.services.campana_notificacion_service import CampanaNotificacionService

                db = SessionLocal()
                try:
                    # Una ejecución interrumpida es reintentable; las entregas tienen
                    # llave idempotente para no repetir destinatarios ya completados.
                    db.query(CampanaNotificacion).filter(
                        CampanaNotificacion.estado == "procesando"
                    ).update({"estado": "programada"})
                    db.commit()
                    CampanaNotificacionService(db).dispatch_due()
                finally:
                    db.close()

            await asyncio.to_thread(run_due_campaigns)
        except Exception as exc:
            print(f"Warning on notification campaign worker: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TestClient reemplaza get_db con una transacción aislada. No se debe tocar
    # la conexión operativa ni iniciar workers externos durante esas pruebas.
    if app.dependency_overrides:
        yield
        return
    # Initialize DB tables and seed default permissions and admin
    try:
        init_db()
    except Exception as e:
        print(f"Warning on startup init_db: {e}")
    stop_event = asyncio.Event()
    worker = asyncio.create_task(_notification_campaign_worker(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await worker


# Create FastAPI application
app = FastAPI(
    title="StyleStore Platform API",
    description="Sistema Full-Stack de Gestión StyleStore (FastAPI + PostgreSQL)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware — permissive for Vercel, Railway, Mobile, Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global error handlers
register_error_handlers(app)

# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")

# Route for serving uploads with database fallback (survives Railway redeployments)
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.uploaded_file import UploadedFile

@app.get("/uploads/{folder}/{filename}", tags=["Uploads"])
async def serve_uploaded_file(folder: str, filename: str, db: Session = Depends(get_db)):
    """Sirve archivos subidos con fallback automático desde base de datos."""
    dest_path = os.path.join(os.getcwd(), "uploads", folder, filename)
    if os.path.exists(dest_path):
        return FileResponse(dest_path)

    # Si no está en disco (ej. contenedor nuevo de Railway), restaurar de la base de datos
    try:
        record = (
            db.query(UploadedFile)
            .filter(UploadedFile.folder == folder, UploadedFile.filename == filename)
            .first()
        )
        if record:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            try:
                with open(dest_path, "wb") as f:
                    f.write(record.data)
            except Exception:
                pass
            return Response(content=record.data, media_type=record.content_type)
    except Exception as e:
        print(f"Error retrieving upload from DB: {e}")

    raise HTTPException(status_code=404, detail="Archivo no encontrado")

# Ensure uploads directory and mount static files as secondary fallback
uploads_dir = os.path.join(os.getcwd(), "uploads")
os.makedirs(os.path.join(uploads_dir, "productos"), exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "empleados"), exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "pagos"), exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "qr"), exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "pruebas"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/", tags=["Root"])
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "StyleStore Auth API is running",
        "docs": "/docs",
    }
