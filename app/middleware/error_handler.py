"""
Global error handler middleware.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging


logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Preserve HTTP exceptions (400, 401, 403, 404, etc.) without converting them to 500."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors without exposing SQL, constraints, or credentials."""
        logger.exception("Database error while handling %s %s", request.method, request.url.path)
        if isinstance(exc, IntegrityError):
            return JSONResponse(
                status_code=409,
                content={
                    "detail": (
                        "Ya existe un registro con esos datos o la operación entra en conflicto "
                        "con información existente."
                    )
                },
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "No se pudo completar la operación. Inténtalo nuevamente."},
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Catch-all handler for unexpected errors."""
        logger.exception("Unexpected error while handling %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocurrió un error inesperado. Inténtalo nuevamente."},
        )
