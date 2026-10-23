"""Regresiones de seguridad para impedir cobros PayPal simulados en producción."""
import asyncio

import pytest

from app.services.paypal_service import PayPalService


def test_mock_paypal_order_is_rejected_by_default():
    service = PayPalService()
    assert service.is_mock_mode() is True

    with pytest.raises(RuntimeError, match="no está configurado"):
        asyncio.run(service.create_order(orden_id=99, total=10))


def test_mock_paypal_capture_is_rejected_by_default():
    result = asyncio.run(PayPalService().capture_order("PAYPAL-MOCK-99"))
    assert result["status"] == "FAILED"
    assert "simulado" in result["error"]


def test_mock_paypal_remains_available_only_when_explicitly_allowed():
    service = PayPalService()
    order = asyncio.run(
        service.create_order(orden_id=99, total=10, allow_fallback=True)
    )
    capture = asyncio.run(service.capture_order(order["id"], allow_mock=True))
    assert order["mock"] is True
    assert capture["status"] == "COMPLETED"
