"""The PayPal status endpoint reports readiness without leaking credentials."""


def test_paypal_status_is_safe_and_reports_test_mode(client, admin_token):
    response = client.get(
        "/api/v1/pagos/paypal/estado",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "sandbox"
    assert payload["sandbox"] is True
    assert payload["mock_enabled"] is True
    assert "client_id" not in payload
    assert "client_secret" not in payload
