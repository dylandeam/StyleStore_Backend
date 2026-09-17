"""
Global error handler middleware.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

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
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred."},
        )
