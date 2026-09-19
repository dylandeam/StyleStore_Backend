"""
Email utility service for notifications and confirmation links.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger("email_service")


def send_password_change_email(to_email: str, confirm_url: str) -> bool:
    """
    Send a password change confirmation email with a one-time link.
    If SMTP credentials are not configured, logs the link for development.
    """
    subject = "StyleStore - Confirmación de cambio de contraseña"
    
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
            <a href="{confirm_url}" class="button" target="_blank">Confirmar Cambio de Contraseña</a>
          </p>
          <div class="alert">
            Este enlace es de un solo uso y expirará en <strong>15 minutos</strong>. Si no solicitaste este cambio, puedes ignorar este mensaje; tu contraseña actual no será modificada.
          </div>
          <p>O copia y pega este enlace en tu navegador:<br><span style="word-break: break-all; color: #4f46e5;">{confirm_url}</span></p>
        </div>
        <div class="footer">
          &copy; StyleStore. Todos los derechos reservados.
        </div>
      </div>
    </body>
    </html>
    """

    # If SMTP is not fully configured, log to console
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            f"[SMTP NOT CONFIGURED] Email simulated to {to_email}. Confirmation URL: {confirm_url}"
        )
        print(f"\n==========================================")
        print(f"[EMAIL SIMULATION] To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Confirmation URL: {confirm_url}")
        print(f"==========================================\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.FROM_EMAIL
        msg["To"] = to_email

        part_html = MIMEText(html_content, "html")
        msg.attach(part_html)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"Password reset confirmation email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        # Print fallback link so user/tester can still confirm
        print(f"\n[EMAIL SEND ERROR FALLBACK] To: {to_email} | URL: {confirm_url}\n")
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
    button_html = ""
    if action_url:
        button_html = f"""
        <p style="text-align: center; margin: 25px 0;">
          <a href="{action_url}" style="background-color: #14263D; color: #FAF7F2; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; display: inline-block;">
            {action_text}
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
        <div class="title">{title}</div>
        <div class="content">
          <p>{message}</p>
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

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.info(f"[SMTP NOT CONFIGURED] Notificación simulada a {to_email}: {title}")
        print(f"\n==========================================")
        print(f"[NOTIFICACION SIMULADA] To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Title: {title}")
        print(f"Message: {message}")
        if action_url:
            print(f"Action URL: {action_url}")
        print(f"==========================================\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.FROM_EMAIL
        msg["To"] = to_email

        part_html = MIMEText(html_content, "html")
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
