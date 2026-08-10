"""Transactional email via Brevo's HTTP API.

Uses HTTPS, not SMTP — Render's free tier blocks outbound SMTP ports
(25/465/587) but HTTPS/443 is unrestricted, so this works there.
"""
from __future__ import annotations

import httpx

from ..config import get_settings

_API = "https://api.brevo.com/v3/smtp/email"
_TIMEOUT = 10.0


class EmailSendError(Exception):
    pass


def _send(*, to_email: str, to_name: str, subject: str, html: str, text: str) -> None:
    settings = get_settings()
    if not settings.brevo_api_key or not settings.brevo_sender_email:
        raise EmailSendError("BREVO_API_KEY / BREVO_SENDER_EMAIL not configured")

    payload = {
        "sender": {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text,
    }
    headers = {
        "api-key": settings.brevo_api_key,
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as c:
            resp = c.post(_API, headers=headers, json=payload)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise EmailSendError(f"Brevo {e.response.status_code}: {e.response.text}") from e
    except httpx.HTTPError as e:
        raise EmailSendError(str(e)) from e


def send_invite_email(*, to_email: str, to_name: str, org_name: str, invite_url: str) -> None:
    """Send the 'you've been given access to Pulse' invite email.

    Raises EmailSendError on failure; the caller decides whether to swallow it
    (account creation should not fail just because the email didn't send).
    """
    settings = get_settings()
    expiry = _format_expiry(settings.invite_ttl_hours)
    _send(
        to_email=to_email,
        to_name=to_name,
        subject="You've been given access to Pulse",
        html=_wrap_html(
            to_name,
            f"You've been given access to <strong>Pulse</strong> for <strong>{org_name}</strong>. "
            "Click below to set your password and get started.",
            invite_url,
            "Accept invite &amp; set password",
            expiry,
        ),
        text=_wrap_text(
            to_name,
            f"You've been given access to Pulse for {org_name}.",
            invite_url,
            expiry,
        ),
    )


def send_reset_password_email(*, to_email: str, to_name: str, reset_url: str) -> None:
    """Send a 'reset your Pulse password' email. Raises EmailSendError on failure."""
    settings = get_settings()
    expiry = _format_expiry(settings.reset_ttl_hours)
    _send(
        to_email=to_email,
        to_name=to_name,
        subject="Reset your Pulse password",
        html=_wrap_html(
            to_name,
            "We received a request to reset your Pulse password. Click below to choose a new one.",
            reset_url,
            "Reset password",
            expiry,
        ),
        text=_wrap_text(
            to_name,
            "We received a request to reset your Pulse password.",
            reset_url,
            expiry,
        ),
    )


def _format_expiry(hours: int) -> str:
    if hours % 24 == 0 and hours >= 24:
        days = hours // 24
        return f"{days} day{'s' if days != 1 else ''}"
    return f"{hours} hour{'s' if hours != 1 else ''}"


def _wrap_text(to_name: str, body: str, url: str, expiry: str) -> str:
    return (
        f"Hi {to_name},\n\n"
        f"{body}\n"
        f"{url}\n\n"
        f"This link expires in {expiry}. If you weren't expecting this, you can ignore this email."
    )


def _wrap_html(to_name: str, body: str, url: str, cta: str, expiry: str) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px">
      <h2 style="color:#003D8F;margin-bottom:4px">Pulse</h2>
      <p style="color:#666;font-size:13px;text-transform:uppercase;letter-spacing:.05em">
        Design Intelligence Platform</p>
      <p style="font-size:15px;color:#222;line-height:1.5">Hi {to_name},</p>
      <p style="font-size:15px;color:#222;line-height:1.5">{body}</p>
      <p style="margin:28px 0">
        <a href="{url}"
           style="background:#003D8F;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;font-weight:600;display:inline-block">
          {cta}
        </a>
      </p>
      <p style="font-size:13px;color:#888;line-height:1.5">
        This link expires in {expiry}. If you weren't expecting this, you can ignore this email.</p>
    </div>
    """
