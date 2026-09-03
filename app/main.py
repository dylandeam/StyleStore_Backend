"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_v1_router
from app.middleware.error_handler import register_error_handlers

# Create FastAPI application
app = FastAPI(
    title="StyleStore Auth API",
    description="Sistema de autenticación Full-Stack con FastAPI + PostgreSQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
