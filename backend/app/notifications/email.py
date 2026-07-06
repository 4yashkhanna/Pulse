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


def send_invite_email(*, to_email: str, to_name: str, org_name: str, invite_url: str) -> None:
    """Send the 'you've been given access to Pulse' invite email.

    Raises EmailSendError on failure; the caller decides whether to swallow it
    (account creation should not fail just because the email didn't send).
    """
    settings = get_settings()
    if not settings.brevo_api_key or not settings.brevo_sender_email:
        raise EmailSendError("BREVO_API_KEY / BREVO_SENDER_EMAIL not configured")

    payload = {
        "sender": {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": "You've been given access to Pulse",
        "htmlContent": _invite_html(to_name, org_name, invite_url),
        "textContent": _invite_text(to_name, org_name, invite_url),
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
