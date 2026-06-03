"""Dashboard API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..db import get_conn
from . import metrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/employee/{user_id}")
def employee(user_id: str):
    return metrics.employee_view(user_id)


@router.get("/manager/{dept}")
def manager(dept: str):
    return metrics.manager_view(dept)


@router.get("/leadership")
def leadership():
    return metrics.leadership_view()


@router.get("/users")
def users():
    """Helper for the frontend: list the mock cohort + their departments."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, dept, role, sector FROM users ORDER BY dept, name"
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "dept": r["dept"],
            "role": r["role"],
            "sector": r["sector"],
        }
        for r in rows
    ]


@router.get("/depts")
def depts():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT dept FROM users WHERE dept IS NOT NULL ORDER BY dept"
        ).fetchall()
    return [r["dept"] for r in rows]
