"""
Application configuration loaded from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory if it exists
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


def _format_db_url(url: str | None) -> str:
    """Ensure database URL starts with postgresql:// instead of postgres://"""
    if not url:
        return "postgresql://postgres:021405@localhost:5432/stylestore_db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = _format_db_url(os.getenv("DATABASE_URL"))
    DATABASE_URL_TEST: str = _format_db_url(
        os.getenv("DATABASE_URL_TEST", "postgresql://postgres:021405@localhost:5432/stylestore_db_test")
    )

    # JWT
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "stylestore-super-secret-key-change-in-production-2024"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # CORS
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:4200,http://localhost:8000,*"
        ).split(",")
        if origin.strip()
    ]

    # SMTP / Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", os.getenv("SMTP_USER", "noreply@stylestore.com"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:4200")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
