"""Transactional email via Gmail SMTP (stdlib smtplib — no external API)."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import get_settings


class EmailSendError(Exception):
    pass


def send_invite_email(*, to_email: str, to_name: str, org_name: str, invite_url: str) -> None:
    """Send the 'you've been given access to Pulse' invite email.

    Raises EmailSendError on failure; the caller decides whether to swallow it
    (account creation should not fail just because the email didn't send).
    """
    settings = get_settings()
    if not settings.smtp_user or not settings.smtp_password:
        raise EmailSendError("SMTP_USER / SMTP_PASSWORD not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "You've been given access to Pulse"
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(_invite_text(to_name, org_name, invite_url), "plain"))
    msg.attach(MIMEText(_invite_html(to_name, org_name, invite_url), "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, [to_email], msg.as_string())
    except (smtplib.SMTPException, OSError) as e:
        raise EmailSendError(str(e)) from e


def _invite_text(to_name: str, org_name: str, invite_url: str) -> str:
    return (
        f"Hi {to_name},\n\n"
        f"You've been given access to Pulse for {org_name}.\n"
        f"Set your password and get started here:\n{invite_url}\n\n"
        f"This link expires in 7 days. If you weren't expecting this, you can ignore this email."
    )


def _invite_html(to_name: str, org_name: str, invite_url: str) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
      <h2 style="color:#003D8F;margin-bottom:4px">Pulse</h2>
      <p style="color:#666;font-size:13px;text-transform:uppercase;letter-spacing:.05em">
        Design Intelligence Platform</p>
      <p style="font-size:15px;color:#222;line-height:1.5">Hi {to_name},</p>
      <p style="font-size:15px;color:#222;line-height:1.5">
        You've been given access to <strong>Pulse</strong> for <strong>{org_name}</strong>.
        Click below to set your password and get started.</p>
      <p style="margin:28px 0">
        <a href="{invite_url}"
           style="background:#003D8F;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;font-weight:600;display:inline-block">
          Accept invite &amp; set password
        </a>
      </p>
      <p style="font-size:13px;color:#888;line-height:1.5">
        This link expires in 7 days. If you weren't expecting this, you can ignore this email.</p>
    </div>
    """
