"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/", tags=["Root"])
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "StyleStore Auth API is running",
        "docs": "/docs",
    }
