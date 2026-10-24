"""
Endpoints del Chatbot Inteligente Local (v6 Punto 4).
Opera en local, responde a consultas y retorna chips de navegación clicables.
"""
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.chatbot_service import ChatbotService
from app.services.plan_service import PlanService
from app.api.deps import get_optional_current_user
from app.config import settings
from datetime import datetime, timezone

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.get("/estado", summary="Estado del motor híbrido del chatbot")
async def estado_chatbot():
    return {
        "modo_preferido": "online_groq" if bool(settings.GROQ_API_KEY) else "online_local",
        "groq_configurado": bool(settings.GROQ_API_KEY),
        "modelo_groq": settings.GROQ_MODEL if settings.GROQ_API_KEY else None,
        "fallback": "reglas_locales",
    }


class MensajeChatbotRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=500, description="Pregunta del usuario")


@router.post("/mensaje", summary="Enviar mensaje al chatbot local y recibir respuesta con chips de navegación")
@router.post("/conversar", summary="Enviar mensaje al chatbot local (alias)", include_in_schema=False)
async def enviar_mensaje_chatbot(
    payload: MensajeChatbotRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Procesa un mensaje con el motor local y retorna respuesta y acciones."""
    if current_user is not None and current_user.empresa_id is not None:
        PlanService(db).require_capability(current_user, "chatbot")
    service = ChatbotService(db)
    resultado = service.responder(payload.mensaje, user=current_user)
    resultado.setdefault("modo_ia", "online_groq" if resultado.get("ia_powered") else "online_local")
    resultado.setdefault("proveedor_ia", "groq" if resultado.get("ia_powered") else "reglas_locales")
    resultado.setdefault("datos_actualizados_en", datetime.now(timezone.utc).isoformat())
    return resultado
