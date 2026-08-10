"""Dashboard routes — permission-gated by the org's visibility settings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth.security import CurrentUser, get_current_user
from ..db import get_conn
from . import metrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def require_org_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dashboards are for organization users")
    return user


def _org_settings(org_id: str) -> dict:
    with get_conn() as conn:
        r = conn.execute("SELECT settings FROM organizations WHERE id = %s", (org_id,)).fetchone()
    return (r["settings"] if r else {}) or {}


@router.get("/me")
def my_dashboard(user: CurrentUser = Depends(require_org_user)):
    """The current user's own individual dashboard.
    Employees get an encouragement-focused view — no polarity scores or signal labels.
    Managers get the full analytical view."""
    if user.role == "employee":
        return {
            "view": "encouragement",
            "role": user.role,
            **metrics.encouragement_view(user.org_id, user.id, user.name),  # type: ignore[arg-type]
        }
    return {
        "view": "individual",
        "role": user.role,
        "can_see_team": user.role == "manager" or _org_settings(user.org_id).get("employee_can_see_team", False),  # type: ignore[arg-type]
        **metrics.individual_view(user.org_id, user.id, user.name),  # type: ignore[arg-type]
    }


@router.get("/team")
def team_dashboard(user: CurrentUser = Depends(require_org_user)):
    """Combined team dashboard. Managers see per-member breakdown; employees see the
    combined view only if the org allows it."""
    if not user.team_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not assigned to a team")
    settings = _org_settings(user.org_id)  # type: ignore[arg-type]
    if user.role == "manager":
        include_members = settings.get("manager_can_see_members", True)
    elif settings.get("employee_can_see_team", False):
        include_members = False  # employees never see per-member, only the combined view
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Team dashboard not visible to employees in this org")
    return metrics.team_view(user.org_id, user.team_id, include_members=include_members)  # type: ignore[arg-type]


@router.get("/member/{member_id}")
def member_dashboard(member_id: str, user: CurrentUser = Depends(require_org_user)):
    """A manager viewing one team member's individual dashboard."""
    if user.role != "manager":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Managers only")
    settings = _org_settings(user.org_id)  # type: ignore[arg-type]
    if not settings.get("manager_can_see_members", True):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Per-member visibility is disabled for this org")
    with get_conn() as conn:
        r = conn.execute(
            "SELECT name FROM users WHERE id = %s AND org_id = %s AND team_id = %s",
            (member_id, user.org_id, user.team_id),
        ).fetchone()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a member of your team")
    return {"view": "individual", **metrics.individual_view(user.org_id, member_id, r["name"])}  # type: ignore[arg-type]
