"""Seed Pulse for the multi-tenant prototype:

1. apply the schema
2. create a KPMG admin account
3. create one demo organization with a team, a manager, and two employees

Knowledge is NOT seeded here — a KPMG admin uploads it through the Admin Portal GUI.

Run from the backend dir:  cd backend && python ../scripts/seed.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.auth.security import hash_password  # noqa: E402
from app.db import get_conn, get_pool  # noqa: E402

SCHEMA = BACKEND.parent / "supabase" / "schema.sql"
PW = "pulse1234"

KPMG_ADMIN = ("admin@kpmg.com", "Dana Kapoor (KPMG)")
DEMO_ORG = {
    "name": "Northwind Retail",
    "maturity_stage": 2,
    "maturity_label": "Designs for aesthetics",
    "description": "Mid-size retailer. Strong visual brand, weak on evidence-backed "
    "decisions. Target: move from designing for aesthetics to designing for strategy.",
    "coach_prompt": "This organization is at Stage 2. Push them from aesthetic instinct "
    "toward validating the problem and grounding decisions in real shopper behaviour. "
    "Be encouraging but insist on evidence before commitment.",
}
MANAGER = ("maya@northwind.com", "Maya Lindqvist")
EMPLOYEES = [("raj@northwind.com", "Raj Mehta"), ("ana@northwind.com", "Ana Duarte")]


def apply_schema() -> None:
    with get_conn() as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        conn.commit()
    print(f"✓ schema applied from {SCHEMA.name}")


def reset() -> None:
    with get_conn() as conn:
        # Cascades clear orgs → users/teams/knowledge/conversations/interactions.
        conn.execute("DELETE FROM organizations")
        conn.execute("DELETE FROM users WHERE org_id IS NULL")  # KPMG admins
        conn.commit()


def seed_baseline(org_id: str) -> None:
    """Seed ONLY the assessment baseline (the starting line from the maturity assessment).
    No synthetic conversations — dashboard scores come exclusively from real coach usage."""
    with get_conn() as conn:
        baseline = {"values": 46, "behavior": 40, "climate": 50, "process": 38, "resources": 44, "success": 39}
        for pillar, score in baseline.items():
            conn.execute(
                "INSERT INTO baseline (org_id, scope, pillar, score) VALUES (%s,'org',%s,%s)",
                (org_id, pillar, score),
            )
        conn.commit()
    print("✓ assessment baseline seeded (no synthetic activity — scores come from real chats)")


def seed() -> tuple[str, list[str]]:
    org_user_ids: list[str] = []
    with get_conn() as conn:
        # KPMG admin (no org).
        conn.execute(
            "INSERT INTO users (org_id, email, password_hash, name, role) "
            "VALUES (NULL,%s,%s,%s,'kpmg_admin')",
            (KPMG_ADMIN[0], hash_password(PW), KPMG_ADMIN[1]),
        )
        # Demo org.
        org = conn.execute(
            """
            INSERT INTO organizations (name, maturity_stage, maturity_label, description, coach_prompt)
            VALUES (%(name)s,%(maturity_stage)s,%(maturity_label)s,%(description)s,%(coach_prompt)s)
            RETURNING id
            """,
            DEMO_ORG,
        ).fetchone()
        org_id = str(org["id"])
        # Team.
        team = conn.execute(
            "INSERT INTO teams (org_id, name) VALUES (%s,'Product') RETURNING id", (org_id,)
        ).fetchone()
        team_id = str(team["id"])
        # Manager.
        mgr = conn.execute(
            "INSERT INTO users (org_id, email, password_hash, name, role, team_id) "
            "VALUES (%s,%s,%s,%s,'manager',%s) RETURNING id",
            (org_id, MANAGER[0], hash_password(PW), MANAGER[1], team_id),
        ).fetchone()
        conn.execute("UPDATE teams SET manager_user_id = %s WHERE id = %s", (str(mgr["id"]), team_id))
        org_user_ids.append(str(mgr["id"]))
        # Employees.
        for email, name in EMPLOYEES:
            emp = conn.execute(
                "INSERT INTO users (org_id, email, password_hash, name, role, team_id) "
                "VALUES (%s,%s,%s,%s,'employee',%s) RETURNING id",
                (org_id, email, hash_password(PW), name, team_id),
            ).fetchone()
            org_user_ids.append(str(emp["id"]))
        conn.commit()
    print("✓ KPMG admin + demo org seeded")
    return org_id, org_user_ids


def main() -> None:
    try:
        apply_schema()
        reset()
        org_id, org_user_ids = seed()
        seed_baseline(org_id)
        print("\nAccounts (password for all: pulse1234)")
        print(f"  KPMG admin : {KPMG_ADMIN[0]}")
        print(f"  Manager    : {MANAGER[0]}")
        print(f"  Employees  : {', '.join(e[0] for e in EMPLOYEES)}")
    finally:
        get_pool().close()


if __name__ == "__main__":
    main()
