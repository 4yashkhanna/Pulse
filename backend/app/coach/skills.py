"""Skills — admin-authored slash-command behaviours (like /design-thinking).

A skill is a named instruction body. KPMG admins create them and grant them per-org.
An org user starts a chat with /command and the skill is pinned to that conversation:
its body is injected into the system prompt for every turn of the chat.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth.security import CurrentUser, get_current_user, require_kpmg_admin
from ..db import get_conn

router = APIRouter(prefix="/skills", tags=["skills"])

DESIGN_THINKING_BODY = """ACTIVE SKILL: Design Thinking Process. For this entire \
conversation you must run a strict, phase-by-phase design-thinking engagement:

1. EMPATHIZE — first establish who the user/customer actually is and what evidence \
exists about their needs. Do not move on until the person has named real users and at \
least one source of real evidence (observation, interviews, data). If they have none, \
your only output is a concrete plan to gather it.
2. DEFINE — force a sharp problem statement: "[User] needs [need] because [insight]". \
Reject vague or solution-shaped statements and have them rewrite until it is testable.
3. IDEATE — only after a defined problem. Push for breadth: at least 5 distinct \
directions before any evaluation. Defer judgment; no committing to the first idea.
4. PROTOTYPE — pick 1-2 directions and define the cheapest artifact that can test the \
riskiest assumption. Push fidelity DOWN, not up.
5. TEST — plan a real test with real users (this is a human handoff: you do not \
simulate results). Define success criteria before the test.

RULES: announce which phase you are in at the start of every reply (e.g. "Phase 2 — \
Define"). Refuse to skip ahead — if the person jumps to solutions, name it and pull \
them back to the current phase. One phase at a time; summarise what was established \
before advancing. Keep each reply focused on moving the current phase forward."""


class SkillCreate(BaseModel):
    name: str
    command: str
    description: str = ""
    body: str


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    body: str | None = None


def _row(r) -> dict:
    return {
        "id": str(r["id"]),
        "name": r["name"],
        "command": r["command"],
        "description": r["description"],
        "body": r["body"],
    }


def ensure_seed(conn) -> None:
    """Seed the Design Thinking skill if no skills exist yet."""
    if conn.execute("SELECT 1 FROM skills LIMIT 1").fetchone():
        return
    conn.execute(
        "INSERT INTO skills (name, command, description, body) VALUES (%s,%s,%s,%s)",
        (
            "Design Thinking",
            "design-thinking",
            "Run a strict empathize → define → ideate → prototype → test process, one phase at a time.",
            DESIGN_THINKING_BODY,
        ),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Admin CRUD
# --------------------------------------------------------------------------- #
@router.get("", dependencies=[Depends(require_kpmg_admin)])
def list_skills():
    with get_conn() as conn:
        ensure_seed(conn)
        rows = conn.execute(
            """
            SELECT s.*, (SELECT COUNT(*) FROM org_skills og WHERE og.skill_id = s.id) AS n_orgs
            FROM skills s ORDER BY s.created_at
            """
        ).fetchall()
    return [{**_row(r), "n_orgs": int(r["n_orgs"])} for r in rows]


@router.post("", status_code=201, dependencies=[Depends(require_kpmg_admin)])
def create_skill(body: SkillCreate):
    command = body.command.strip().lstrip("/").lower().replace(" ", "-")
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM skills WHERE command=%s", (command,)).fetchone():
            raise HTTPException(status.HTTP_409_CONFLICT, "That command already exists")
        r = conn.execute(
            "INSERT INTO skills (name, command, description, body) VALUES (%s,%s,%s,%s) RETURNING *",
            (body.name, command, body.description, body.body),
        ).fetchone()
        conn.commit()
    return _row(r)


@router.patch("/{skill_id}", dependencies=[Depends(require_kpmg_admin)])
def update_skill(skill_id: str, body: SkillUpdate):
    fields, values = [], []
    for col in ("name", "description", "body"):
        v = getattr(body, col)
        if v is not None:
            fields.append(f"{col} = %s")
            values.append(v)
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to update")
    values.append(skill_id)
    with get_conn() as conn:
        r = conn.execute(
            f"UPDATE skills SET {', '.join(fields)} WHERE id = %s RETURNING *", values
        ).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")
    return _row(r)


@router.delete("/{skill_id}", dependencies=[Depends(require_kpmg_admin)])
def delete_skill(skill_id: str):
    with get_conn() as conn:
        r = conn.execute("DELETE FROM skills WHERE id=%s RETURNING id", (skill_id,)).fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill not found")
    return {"deleted": skill_id}


# --------------------------------------------------------------------------- #
# Org grants (admin)
# --------------------------------------------------------------------------- #
@router.get("/grants/{org_id}", dependencies=[Depends(require_kpmg_admin)])
def org_grants(org_id: str):
    with get_conn() as conn:
        ensure_seed(conn)
        rows = conn.execute(
            """
            SELECT s.id, s.name, s.command, s.description,
                   (og.skill_id IS NOT NULL) AS granted
            FROM skills s
            LEFT JOIN org_skills og ON og.skill_id = s.id AND og.org_id = %s
            ORDER BY s.created_at
            """,
            (org_id,),
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "command": r["command"],
            "description": r["description"],
            "granted": bool(r["granted"]),
        }
        for r in rows
    ]


@router.post("/grants/{org_id}/{skill_id}", dependencies=[Depends(require_kpmg_admin)])
def grant(org_id: str, skill_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO org_skills (org_id, skill_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (org_id, skill_id),
        )
        conn.commit()
    return {"granted": True}


@router.delete("/grants/{org_id}/{skill_id}", dependencies=[Depends(require_kpmg_admin)])
def revoke(org_id: str, skill_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM org_skills WHERE org_id=%s AND skill_id=%s", (org_id, skill_id))
        conn.commit()
    return {"granted": False}


# --------------------------------------------------------------------------- #
# Org users: which skills can I use?
# --------------------------------------------------------------------------- #
@router.get("/mine")
def my_skills(user: CurrentUser = Depends(get_current_user)):
    if not user.org_id:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.name, s.command, s.description
            FROM skills s JOIN org_skills og ON og.skill_id = s.id
            WHERE og.org_id = %s ORDER BY s.name
            """,
            (user.org_id,),
        ).fetchall()
    return [
        {"id": str(r["id"]), "name": r["name"], "command": r["command"], "description": r["description"]}
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Used by the chat pipeline
# --------------------------------------------------------------------------- #
def resolve_command(conn, org_id: str, command: str) -> dict | None:
    """A granted skill for this org by its slash command, or None."""
    r = conn.execute(
        """
        SELECT s.id, s.name, s.command, s.body
        FROM skills s JOIN org_skills og ON og.skill_id = s.id AND og.org_id = %s
        WHERE s.command = %s
        """,
        (org_id, command.lower()),
    ).fetchone()
    return _row({**r, "description": ""}) if r else None


def skill_for_conversation(conn, conversation_id: str) -> dict | None:
    r = conn.execute(
        """
        SELECT s.id, s.name, s.command, s.body FROM conversations c
        JOIN skills s ON s.id = c.skill_id WHERE c.id = %s
        """,
        (conversation_id,),
    ).fetchone()
    return _row({**r, "description": ""}) if r else None
