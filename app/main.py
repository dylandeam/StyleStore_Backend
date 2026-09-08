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

# Ensure uploads directory and mount static files
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
