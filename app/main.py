"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_v1_router
from app.middleware.error_handler import register_error_handlers
from app.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed default permissions and admin
    try:
        init_db()
    except Exception as e:
        print(f"Warning on startup init_db: {e}")
    yield


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
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/", tags=["Root"])
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "StyleStore Auth API is running",
        "docs": "/docs",
    }
