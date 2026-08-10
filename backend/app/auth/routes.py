"""Auth routes: login (rate-limited), who-am-I, change password, accept-invite,
forgot/reset password."""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from ..config import get_settings
from ..db import get_conn
from ..notifications.email import EmailSendError, send_reset_password_email
from .security import (
    CurrentUser,
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# --- simple in-process rate limiter (per email and per client IP) -------------
# Good enough for a single-process deployment; swap for Redis when scaling out.
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
_attempts: dict[str, deque[float]] = defaultdict(deque)


def _rate_limited(key: str) -> bool:
    now = time.monotonic()
    q = _attempts[key]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_ATTEMPTS:
        return True
    q.append(now)
    return False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AcceptInviteRequest(BaseModel):
    token: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def _user_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "org_id": str(row["org_id"]) if row["org_id"] else None,
        "team_id": str(row["team_id"]) if row["team_id"] else None,
    }


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(f"email:{req.email.lower()}") or _rate_limited(f"ip:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many login attempts. Wait a minute and try again.",
        )
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, email, name, role, org_id, team_id, password_hash FROM users WHERE email = %s",
            (req.email.lower(),),
        ).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = create_token(str(row["id"]))
    return LoginResponse(token=token, user=_user_dict(row))


@router.post("/accept-invite", response_model=LoginResponse)
def accept_invite(req: AcceptInviteRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(f"invite:{req.token[:8]}") or _rate_limited(f"ip:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many attempts. Wait a minute and try again.",
        )
    if len(req.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters")
    token_hash = hashlib.sha256(req.token.encode()).hexdigest()
    with get_conn() as conn:
        invite = conn.execute(
            """
            SELECT id, user_id FROM user_invites
            WHERE token_hash = %s AND accepted_at IS NULL AND expires_at > now()
            """,
            (token_hash,),
        ).fetchone()
        if not invite:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This invite link is invalid or has expired")
        conn.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(req.new_password), invite["user_id"]),
        )
        conn.execute("UPDATE user_invites SET accepted_at = now() WHERE id = %s", (invite["id"],))
        row = conn.execute(
            "SELECT id, email, name, role, org_id, team_id FROM users WHERE id = %s",
            (invite["user_id"],),
        ).fetchone()
        conn.commit()
    token = create_token(str(row["id"]))
    return LoginResponse(token=token, user=_user_dict(row))


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request):
    """Always returns a generic response, whether or not the email exists —
    prevents leaking which emails have Pulse accounts."""
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(f"forgot:{req.email.lower()}") or _rate_limited(f"ip:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many attempts. Wait a minute and try again.",
        )
    settings = get_settings()
    with get_conn() as conn:
        user = conn.execute(
            "SELECT id, name FROM users WHERE email = %s", (req.email.lower(),)
        ).fetchone()
        if user:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=settings.reset_ttl_hours)
            conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (%s,%s,%s)",
                (user["id"], token_hash, expires_at),
            )
            conn.commit()
            reset_url = f"{settings.frontend_origin}/reset-password?token={token}"
            if settings.env != "prod":
                logger.warning("[DEV] reset link for %s: %s", req.email.lower(), reset_url)
            try:
                send_reset_password_email(to_email=req.email.lower(), to_name=user["name"], reset_url=reset_url)
            except EmailSendError as e:
                logger.warning("reset email failed for %s: %s", req.email.lower(), e)
    return {"sent": True}


@router.post("/reset-password", response_model=LoginResponse)
def reset_password(req: ResetPasswordRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(f"reset:{req.token[:8]}") or _rate_limited(f"ip:{client_ip}"):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many attempts. Wait a minute and try again.",
        )
    if len(req.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters")
    token_hash = hashlib.sha256(req.token.encode()).hexdigest()
    with get_conn() as conn:
        reset = conn.execute(
            """
            SELECT id, user_id FROM password_resets
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()
            """,
            (token_hash,),
        ).fetchone()
        if not reset:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")
        conn.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(req.new_password), reset["user_id"]),
        )
        conn.execute("UPDATE password_resets SET used_at = now() WHERE id = %s", (reset["id"],))
        row = conn.execute(
            "SELECT id, email, name, role, org_id, team_id FROM users WHERE id = %s",
            (reset["user_id"],),
        ).fetchone()
        conn.commit()
    token = create_token(str(row["id"]))
    return LoginResponse(token=token, user=_user_dict(row))


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, user: CurrentUser = Depends(get_current_user)):
    if len(req.new_password) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password must be at least 8 characters")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (user.id,)
        ).fetchone()
        if not row or not verify_password(req.current_password, row["password_hash"]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")
        conn.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(req.new_password), user.id),
        )
        conn.commit()
    return {"changed": True}


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "org_id": user.org_id,
        "team_id": user.team_id,
    }
