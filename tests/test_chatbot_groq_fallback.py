from app.config import settings
from app.services.chatbot_service import ChatbotService


def test_chatbot_uses_local_fallback_when_groq_is_unavailable(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "configured-but-unavailable")
    monkeypatch.setattr(
        ChatbotService,
        "_consultar_groq",
        lambda self, mensaje, user=None: None,
    )

    response = client.post(
        "/api/v1/chatbot/mensaje",
        json={"mensaje": "¿Qué métodos de pago aceptan?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["modo_ia"] == "online_local"
    assert data["proveedor_ia"] == "reglas_locales"
    assert data["ia_powered"] is False
    assert "PayPal" in data["respuesta"]
