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
from app.api.deps import get_optional_current_user

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class MensajeChatbotRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=500, description="Pregunta del usuario")


@router.post("/mensaje", summary="Enviar mensaje al chatbot local y recibir respuesta con chips de navegación")
async def enviar_mensaje_chatbot(
    payload: MensajeChatbotRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Procesa un mensaje con el motor local y retorna respuesta y acciones."""
    service = ChatbotService(db)
    resultado = service.responder(payload.mensaje, user=current_user)
    return resultado
