"""Seed Pulse for a demo:

1. (optionally) apply the schema
2. ingest the KPMG knowledge markdown into pgvector
3. create a mock cohort of users across departments
4. seed a mocked assessment baseline
5. generate synthetic interactions (spread over recent months, trending up) so the
   team and leadership dashboards are populated on first load

Run from the backend dir after installing requirements and setting backend/.env:

    cd backend && python ../scripts/seed.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

# Make `app` importable regardless of cwd.
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import DT_PHASES, PILLAR_WEIGHTS, USAGE_TYPES  # noqa: E402
from app.db import get_conn  # noqa: E402
from app.rag.ingest import ingest_paths  # noqa: E402

PILLARS = list(PILLAR_WEIGHTS.keys())
DATA_DIR = BACKEND / "data"
SCHEMA = BACKEND.parent / "supabase" / "schema.sql"

USERS = [
    # (name, dept, role, sector)
    ("Aanya Rao", "Product Design", "Senior Designer", "it"),
    ("Marcus Bell", "Product Design", "Designer", "it"),
    ("Priya Nair", "Product Design", "Design Lead", "it"),
    ("Tom Fischer", "Innovation", "Innovation Manager", "fmcg"),
    ("Lena Ortiz", "Innovation", "Strategist", "fmcg"),
    ("Sam Whitfield", "Innovation", "Researcher", "fmcg"),
    ("Ishaan Gupta", "Engineering UX", "UX Engineer", "it"),
    ("Chloe Adams", "Engineering UX", "Frontend Lead", "it"),
]


def apply_schema() -> None:
    if not SCHEMA.exists():
        return
    sql = SCHEMA.read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.execute(sql)
        conn.commit()
    print(f"✓ schema applied from {SCHEMA.name}")


def seed_users() -> list[str]:
    ids: list[str] = []
    with get_conn() as conn:
        conn.execute("DELETE FROM interactions")
        conn.execute("DELETE FROM users")
        for name, dept, role, sector in USERS:
            row = conn.execute(
                "INSERT INTO users (name, dept, role, sector) VALUES (%s,%s,%s,%s) RETURNING id",
                (name, dept, role, sector),
            ).fetchone()
            ids.append(str(row["id"]))
        conn.commit()
    print(f"✓ {len(ids)} users seeded")
    return ids


def seed_baseline() -> None:
    # Mocked assessment baseline (0-100 per pillar) — the starting line.
    baseline = {
        "values": 48,
        "behavior": 42,
        "climate": 51,
        "process": 39,
        "resources": 45,
        "success": 40,
    }
    with get_conn() as conn:
        conn.execute("DELETE FROM baseline")
        for pillar, score in baseline.items():
            conn.execute(
                "INSERT INTO baseline (scope, pillar, score) VALUES ('org', %s, %s)",
                (pillar, score),
            )
        conn.commit()
    print("✓ baseline seeded")


def seed_interactions(user_ids: list[str], n_per_user: int = 9) -> None:
    """Create synthetic interactions spread over the last 5 months, trending upward
    in quality so the leadership trajectory shows progress above baseline."""
    random.seed(7)
    rows = []
    for uid in user_ids:
        for _ in range(n_per_user):
            months_ago = random.randint(0, 4)
            # Quality drifts up as months_ago decreases (more recent = better).
            base_q = 2.4 + (4 - months_ago) * 0.45
            quality = max(1, min(5, round(random.gauss(base_q, 0.6))))
            rows.append(
                (
                    uid,
                    random.choice(PILLARS),
                    random.choice(DT_PHASES),
                    random.choice(USAGE_TYPES),
                    quality >= 4 and random.random() < 0.7,  # evidence more likely when thoughtful
                    quality,
                    random.random() < 0.15,  # occasional handoff
                    months_ago,
                )
            )
    with get_conn() as conn:
        for uid, pillar, phase, usage, evidence, quality, handoff, months_ago in rows:
            conn.execute(
                """
                INSERT INTO interactions
                    (user_id, pillar, phase, usage_type, evidence_backed, quality_score,
                     handoff, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s, now() - (%s * interval '30 days'))
                """,
                (uid, pillar, phase, usage, evidence, quality, handoff, months_ago),
            )
        conn.commit()
    print(f"✓ {len(rows)} synthetic interactions seeded")


def seed_knowledge() -> None:
    paths = sorted(DATA_DIR.glob("*.md"))
    count = ingest_paths(paths)
    print(f"✓ {count} knowledge chunks ingested from {len(paths)} files")


def main() -> None:
    from app.db import get_pool

    try:
        apply_schema()
        seed_knowledge()
        ids = seed_users()
        seed_baseline()
        seed_interactions(ids)
        print("\nDone. Start the backend (uvicorn app.main:app --reload) and the frontend.")
    finally:
        get_pool().close()


if __name__ == "__main__":
    main()
