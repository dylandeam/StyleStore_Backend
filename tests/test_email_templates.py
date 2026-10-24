from email import message_from_string

from app.core import email as email_service


class FakeSMTP:
    sent_messages: list[str] = []

    def __init__(self, host: str, port: int, timeout: int):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def starttls(self):
        return None

    def login(self, _username: str, _password: str):
        return None

    def sendmail(self, _sender: str, _recipients: list[str], content: str):
        self.sent_messages.append(content)


def _configure_smtp(monkeypatch):
    FakeSMTP.sent_messages.clear()
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "mailer@example.com")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "test-password")
    monkeypatch.setattr(email_service.settings, "FROM_EMAIL", "mailer@example.com")
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)


def _message_parts():
    message = message_from_string(FakeSMTP.sent_messages[-1])
    plain = message.get_payload(0).get_payload(decode=True).decode("utf-8")
    html = message.get_payload(1).get_payload(decode=True).decode("utf-8")
    return message, plain, html


def test_password_email_has_friendly_sender_and_both_formats(monkeypatch):
    _configure_smtp(monkeypatch)
    confirm_url = "https://app.example.com/confirm?token=abc&source=email"

    assert email_service.send_password_change_email("client@example.com", confirm_url)

    message, plain, html = _message_parts()
    assert message["From"] == "StyleStore <mailer@example.com>"
    assert confirm_url in plain
    assert "abc&amp;source=email" in html


def test_notification_email_escapes_untrusted_html(monkeypatch):
    _configure_smtp(monkeypatch)

    assert email_service.send_notification_email(
        "client@example.com",
        "Compra confirmada",
        "Pedido <script>alert(1)</script>",
        "Gracias <img src=x onerror=alert(1)>",
        "https://app.example.com/order?id=1&view=full",
        "Ver <pedido>",
    )

    _, plain, html = _message_parts()
    assert "Pedido <script>alert(1)</script>" in plain
    assert "<script>" not in html
    assert "<img" not in html
    assert "Pedido &lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "id=1&amp;view=full" in html
    assert "Ver &lt;pedido&gt;" in html


def test_password_email_does_not_expose_token_when_smtp_fails(monkeypatch, caplog, capsys):
    _configure_smtp(monkeypatch)
    private_url = "https://app.example.com/confirm?token=very-private-token"

    def fail_to_connect(*_args, **_kwargs):
        raise OSError("connection unavailable")

    monkeypatch.setattr(email_service.smtplib, "SMTP", fail_to_connect)

    assert not email_service.send_password_change_email("client@example.com", private_url)
    captured = capsys.readouterr()
    assert "very-private-token" not in captured.out
    assert "very-private-token" not in captured.err
    assert "very-private-token" not in caplog.text
