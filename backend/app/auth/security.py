"""Auth primitives: password hashing, JWT, and role-guarded dependencies."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings
from ..db import get_conn

bearer = HTTPBearer(auto_error=False)


# --- passwords ---------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# --- tokens ------------------------------------------------------------------
def create_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


# --- current user ------------------------------------------------------------
@dataclass
class CurrentUser:
    id: str
    email: str
    name: str
    role: str
    org_id: str | None
    team_id: str | None


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = _decode(creds.credentials)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, email, name, role, org_id, team_id FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return CurrentUser(
        id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        role=row["role"],
        org_id=str(row["org_id"]) if row["org_id"] else None,
        team_id=str(row["team_id"]) if row["team_id"] else None,
    )


def require_kpmg_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "kpmg_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "KPMG admin access required")
    return user
