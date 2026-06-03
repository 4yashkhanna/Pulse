"""Auth routes: login + who-am-I."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from ..db import get_conn
from .security import CurrentUser, create_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
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
