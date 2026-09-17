"""
Global error handler middleware.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError


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
        """Handle database errors gracefully."""
        import traceback
        traceback.print_exc()
        detail = str(exc)
        if hasattr(exc, "orig") and exc.orig:
            detail = str(exc.orig)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Database error: {detail}"},
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Catch-all handler for unexpected errors."""
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error inesperado: {type(exc).__name__} - {str(exc)}"},
        )
