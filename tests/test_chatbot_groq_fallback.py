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


def test_chatbot_removes_ai_navigation_metadata_and_builds_safe_actions():
    raw = (
        "¡Hola! **Tenemos polos disponibles** 👕\n\n"
        "---\n"
        "**CHIPS:** [Ver Catálogo | /catalogo], "
        "[Nuestras Sucursales | /admin/sucursales]"
    )

    cleaned = ChatbotService._clean_ai_response(raw)
    chips = ChatbotService._navigation_chips("Quiero ver polos y precios")

    assert "CHIPS" not in cleaned
    assert "/catalogo" not in cleaned
    assert "---" not in cleaned
    assert "Tenemos polos disponibles" in cleaned
    assert chips[0] == {
        "label": "Ver catálogo",
        "action": "navigate",
        "route": "/catalogo",
    }
    assert all(chip["route"].startswith("/") for chip in chips)
