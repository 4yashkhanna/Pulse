"""Organization management — KPMG admin only.

Create/manage tenants, provision users + teams, set the org coach prompt and the
dashboard visibility settings.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from ..auth.security import CurrentUser, hash_password, require_kpmg_admin
from ..config import get_settings
from ..db import get_conn
from ..notifications.email import EmailSendError, send_invite_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orgs", tags=["orgs"], dependencies=[Depends(require_kpmg_admin)])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class OrgCreate(BaseModel):
    name: str
    maturity_stage: int = 2
    maturity_label: str = "Designs for aesthetics"
    description: str = ""
    coach_prompt: str = ""


class OrgUpdate(BaseModel):
    name: str | None = None
    maturity_stage: int | None = None
    maturity_label: str | None = None
    description: str | None = None
    coach_prompt: str | None = None
    settings: dict | None = None


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    # When omitted (the normal case), the user is emailed an invite link and
    # sets their own password. Only set this to skip the invite flow entirely.
    password: str | None = None
    role: str = "employee"  # employee | manager
    team_id: str | None = None


class TeamCreate(BaseModel):
    name: str
    manager_user_id: str | None = None


# --------------------------------------------------------------------------- #
# Organizations
# --------------------------------------------------------------------------- #
def _org_row(r) -> dict:
    return {
        "id": str(r["id"]),
        "name": r["name"],
        "maturity_stage": r["maturity_stage"],
        "maturity_label": r["maturity_label"],
        "description": r["description"],
        "coach_prompt": r["coach_prompt"],
        "settings": r["settings"],
        "created_at": r["created_at"].isoformat(),
    }


@router.get("")
def list_orgs():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT o.*,
                   (SELECT COUNT(*) FROM users u WHERE u.org_id = o.id) AS n_users,
                   (SELECT COUNT(*) FROM knowledge_chunks k WHERE k.org_id = o.id) AS n_chunks
            FROM organizations o ORDER BY o.created_at DESC
            """
        ).fetchall()
    out = []
    for r in rows:
        d = _org_row(r)
        d["n_users"] = int(r["n_users"])
        d["n_chunks"] = int(r["n_chunks"])
        out.append(d)
    return out


@router.post("", status_code=201)
def create_org(body: OrgCreate):
    with get_conn() as conn:
        r = conn.execute(
            """
            INSERT INTO organizations (name, maturity_stage, maturity_label, description, coach_prompt)
            VALUES (%s,%s,%s,%s,%s) RETURNING *
            """,
            (body.name, body.maturity_stage, body.maturity_label, body.description, body.coach_prompt),
        ).fetchone()
        conn.commit()
    return _org_row(r)


@router.get("/{org_id}")
def get_org(org_id: str):
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM organizations WHERE id = %s", (org_id,)).fetchone()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return _org_row(r)


@router.patch("/{org_id}")
def update_org(org_id: str, body: OrgUpdate):
    fields, values = [], []
    for col in ("name", "maturity_stage", "maturity_label", "description", "coach_prompt"):
        val = getattr(body, col)
        if val is not None:
            fields.append(f"{col} = %s")
            values.append(val)
    if body.settings is not None:
        fields.append("settings = %s")
        values.append(json.dumps(body.settings))
    if not fields:
        return get_org(org_id)
    values.append(org_id)
    with get_conn() as conn:
        r = conn.execute(
            f"UPDATE organizations SET {', '.join(fields)} WHERE id = %s RETURNING *", values
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")
    return _org_row(r)


# --------------------------------------------------------------------------- #
# Teams
# --------------------------------------------------------------------------- #
@router.get("/{org_id}/teams")
def list_teams(org_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, manager_user_id FROM teams WHERE org_id = %s ORDER BY name",
            (org_id,),
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "manager_user_id": str(r["manager_user_id"]) if r["manager_user_id"] else None,
        }
        for r in rows
    ]


@router.post("/{org_id}/teams", status_code=201)
def create_team(org_id: str, body: TeamCreate):
    with get_conn() as conn:
        r = conn.execute(
            "INSERT INTO teams (org_id, name, manager_user_id) VALUES (%s,%s,%s) RETURNING id",
            (org_id, body.name, body.manager_user_id),
        ).fetchone()
        conn.commit()
    return {"id": str(r["id"]), "name": body.name}


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
def _invite_status(accepted_at, expires_at) -> str:
    if expires_at is None or accepted_at is not None:
        return "active"
    if expires_at > dt.datetime.now(dt.timezone.utc):
        return "pending"
    return "expired"


def _issue_invite(conn, *, user_id: str, org_id: str, org_name: str, email: str, name: str, invited_by: str) -> bool:
    """Expire any prior pending invite for this user, issue a fresh single-use
    token, and email it. Returns whether the email actually sent."""
    settings = get_settings()
    conn.execute(
        "UPDATE user_invites SET expires_at = now() WHERE user_id = %s AND accepted_at IS NULL",
        (user_id,),
    )
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=settings.invite_ttl_hours)
    conn.execute(
        """
        INSERT INTO user_invites (user_id, org_id, token_hash, expires_at, invited_by)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (user_id, org_id, token_hash, expires_at, invited_by),
    )
    invite_url = f"{settings.frontend_origin}/accept-invite?token={token}"
    if settings.env != "prod":
        logger.info("[DEV] invite link for %s: %s", email, invite_url)
    try:
        send_invite_email(to_email=email, to_name=name, org_name=org_name, invite_url=invite_url)
        return True
    except EmailSendError as e:
        logger.warning("invite email failed for %s: %s", email, e)
        return False


@router.get("/{org_id}/users")
def list_users(org_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.name, u.email, u.role, u.team_id, t.name AS team_name,
                   ui.accepted_at, ui.expires_at
            FROM users u
            LEFT JOIN teams t ON t.id = u.team_id
            LEFT JOIN LATERAL (
                SELECT accepted_at, expires_at FROM user_invites
                WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1
            ) ui ON true
            WHERE u.org_id = %s ORDER BY u.role, u.name
            """,
            (org_id,),
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "email": r["email"],
            "role": r["role"],
            "team_id": str(r["team_id"]) if r["team_id"] else None,
            "team_name": r["team_name"],
            "invite_status": _invite_status(r["accepted_at"], r["expires_at"]),
        }
        for r in rows
    ]


@router.post("/{org_id}/users", status_code=201)
def create_user(org_id: str, body: UserCreate, admin: CurrentUser = Depends(require_kpmg_admin)):
    if body.role not in ("employee", "manager"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role must be employee or manager")
    email = body.email.lower()
    with get_conn() as conn:
        existing = conn.execute("SELECT 1 FROM users WHERE email = %s", (email,)).fetchone()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "A user with that email already exists")
        org = conn.execute("SELECT name FROM organizations WHERE id = %s", (org_id,)).fetchone()
        if not org:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

        # No password given (the normal path): the account starts with an unusable
        # random hash and the user sets a real one by accepting an emailed invite.
        initial_password = body.password or secrets.token_urlsafe(32)
        r = conn.execute(
            """
            INSERT INTO users (org_id, email, password_hash, name, role, team_id)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (org_id, email, hash_password(initial_password), body.name, body.role, body.team_id),
        ).fetchone()
        user_id = str(r["id"])
        # If this user is a manager and assigned to a team, set them as the team's manager.
        if body.role == "manager" and body.team_id:
            conn.execute(
                "UPDATE teams SET manager_user_id = %s WHERE id = %s AND org_id = %s",
                (user_id, body.team_id, org_id),
            )

        invite_sent = False
        if not body.password:
            invite_sent = _issue_invite(
                conn,
                user_id=user_id,
                org_id=org_id,
                org_name=org["name"],
                email=email,
                name=body.name,
                invited_by=admin.id,
            )
        conn.commit()
    return {"id": user_id, "email": email, "role": body.role, "invite_sent": invite_sent}


@router.post("/{org_id}/users/{user_id}/resend-invite")
def resend_invite(org_id: str, user_id: str, admin: CurrentUser = Depends(require_kpmg_admin)):
    with get_conn() as conn:
        user = conn.execute(
            """
            SELECT u.name, u.email, o.name AS org_name
            FROM users u JOIN organizations o ON o.id = u.org_id
            WHERE u.id = %s AND u.org_id = %s
            """,
            (user_id, org_id),
        ).fetchone()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        invite_sent = _issue_invite(
            conn,
            user_id=user_id,
            org_id=org_id,
            org_name=user["org_name"],
            email=user["email"],
            name=user["name"],
            invited_by=admin.id,
        )
        conn.commit()
    return {"invite_sent": invite_sent}
