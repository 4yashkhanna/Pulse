"""Auth routes: login (rate-limited), who-am-I, change password."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from ..db import get_conn
from .security import (
    CurrentUser,
    create_token,
    get_current_user,
    hash_password,
    verify_password,
)

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
    return LoginResponse(
        token=token,
        user={
            "id": str(row["id"]),
            "email": row["email"],
            "name": row["name"],
            "role": row["role"],
            "org_id": str(row["org_id"]) if row["org_id"] else None,
            "team_id": str(row["team_id"]) if row["team_id"] else None,
        },
    )


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
