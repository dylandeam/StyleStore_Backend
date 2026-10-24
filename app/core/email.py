"""
Email utility service for notifications and confirmation links.
"""
import smtplib
import logging
import os
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger("email_service")


def email_delivery_configured() -> bool:
    """Return True only when the SMTP sender has usable credentials."""
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _managed_environment() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))


def _sender_header() -> str:
    return formataddr(("StyleStore", settings.FROM_EMAIL))


def send_password_change_email(to_email: str, confirm_url: str) -> bool:
    """
    Send a password change confirmation email with a one-time link.
    If SMTP credentials are not configured, logs the link for development.
    """
    subject = "StyleStore - Confirmación de cambio de contraseña"
    
    safe_confirm_url = escape(confirm_url, quote=True)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
        .header {{ text-align: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 20px; }}
        .header h1 {{ color: #4f46e5; margin: 0; font-size: 24px; font-weight: 700; }}
        .content {{ padding: 24px 0; color: #334155; line-height: 1.6; font-size: 15px; }}
        .button {{ display: inline-block; background-color: #4f46e5; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
        .footer {{ border-top: 1px solid #e2e8f0; padding-top: 16px; font-size: 12px; color: #94a3b8; text-align: center; }}
        .alert {{ background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 16px 0; font-size: 13px; color: #991b1b; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>StyleStore</h1>
        </div>
        <div class="content">
          <p>Hola,</p>
          <p>Hemos recibido una solicitud para actualizar la contraseña de tu cuenta en <strong>StyleStore</strong>.</p>
          <p>Para confirmar el cambio de contraseña, haz clic en el siguiente botón:</p>
          <p style="text-align: center;">
            <a href="{safe_confirm_url}" class="button" target="_blank">Confirmar Cambio de Contraseña</a>
          </p>
          <div class="alert">
            Este enlace es de un solo uso y expirará en <strong>15 minutos</strong>. Si no solicitaste este cambio, puedes ignorar este mensaje; tu contraseña actual no será modificada.
          </div>
          <p>O copia y pega este enlace en tu navegador:<br><span style="word-break: break-all; color: #4f46e5;">{safe_confirm_url}</span></p>
        </div>
        <div class="footer">
          &copy; StyleStore. Todos los derechos reservados.
        </div>
      </div>
    </body>
    </html>
    """

    # If SMTP is not fully configured, log to console
    if not email_delivery_configured():
        if _managed_environment():
            logger.error("SMTP no está configurado en el entorno administrado; no se envió el correo de contraseña.")
            return False
        logger.warning("[SMTP NOT CONFIGURED] Email de contraseña simulado para %s.", to_email)
        if settings.DEBUG:
            print(f"[EMAIL SIMULATION] To: {to_email} | Confirmation URL: {confirm_url}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = _sender_header()
        msg["To"] = to_email

        text_content = (
            "StyleStore\n\nConfirma el cambio de contraseña usando este enlace de un solo uso "
            f"(válido por 15 minutos):\n{confirm_url}\n\n"
            "Si no solicitaste este cambio, ignora este mensaje."
        )
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        part_html = MIMEText(html_content, "html", "utf-8")
        msg.attach(part_html)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"Password reset confirmation email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error("Failed to send password confirmation email to %s: %s", to_email, e)
        return False


def send_notification_email(
    to_email: str,
    subject: str,
    title: str,
    message: str,
    action_url: str | None = None,
    action_text: str = "Ver en StyleStore"
) -> bool:
    """
    Envía un correo de notificación con la identidad visual Beige & Navy de StyleStore.
    Si SMTP no está configurado, registra el correo en consola de forma segura.
    """
    safe_title = escape(title)
    safe_message = escape(message).replace("\n", "<br>")
    safe_action_url = escape(action_url, quote=True) if action_url else None
    safe_action_text = escape(action_text)
    button_html = ""
    if safe_action_url:
        button_html = f"""
        <p style="text-align: center; margin: 25px 0;">
          <a href="{safe_action_url}" style="background-color: #14263D; color: #FAF7F2; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; display: inline-block;">
            {safe_action_text}
          </a>
        </p>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #FAF7F2; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #E8E2D8; box-shadow: 0 4px 6px -1px rgba(20, 38, 61, 0.08); }}
        .header {{ text-align: center; border-bottom: 2px solid #D4AF37; padding-bottom: 16px; margin-bottom: 20px; }}
        .header h1 {{ color: #14263D; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 0.5px; }}
        .title {{ color: #14263D; font-size: 18px; font-weight: 700; margin-bottom: 12px; }}
        .content {{ color: #334155; line-height: 1.6; font-size: 15px; }}
        .footer {{ border-top: 1px solid #E8E2D8; padding-top: 16px; margin-top: 24px; font-size: 12px; color: #64748b; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>STYLESTORE</h1>
        </div>
        <div class="title">{safe_title}</div>
        <div class="content">
          <p>{safe_message}</p>
          {button_html}
        </div>
        <div class="footer">
          &copy; StyleStore. Moda elegante y vanguardista.<br>
          Este es un mensaje automático, por favor no responda directamente a este correo.
        </div>
      </div>
    </body>
    </html>
    """

    if not email_delivery_configured():
        if _managed_environment():
            logger.error("SMTP no está configurado en el entorno administrado; no se envió la confirmación de compra.")
            return False
        logger.info(f"[SMTP NOT CONFIGURED] Notificación simulada a {to_email}: {title}")
        if settings.DEBUG:
            print(f"[NOTIFICACION SIMULADA] To: {to_email} | Subject: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = _sender_header()
        msg["To"] = to_email

        text_content = f"StyleStore\n\n{title}\n\n{message}"
        if action_url:
            text_content += f"\n\n{action_text}: {action_url}"
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        part_html = MIMEText(html_content, "html", "utf-8")
        msg.attach(part_html)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"Notification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification email to {to_email}: {e}")
        return False
