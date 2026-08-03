"""Deterministic demo seed: Maya Lindqvist's (manager) own /design-thinking engagement.

Companion to seed_raj_chat_direct.py. A manager's "My Progress" tab reflects their own coach
usage, which was nearly empty (3 stray empathy turns). This seeds a coherent, lighter
engagement so that tab isn't sparse — Maya works through a real retail design question
(Northwind's in-store pickup experience). Her profile reads like an experienced manager:
collaboration (climate) and user-centeredness (values) are strengths, with a couple of honest
missteps the coach catches (nearly converging early; tempted to call a pilot a win too soon).

Run from the backend dir:  cd backend && python ../scripts/seed_maya_chat_direct.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.coach.signals import BY_ID  # noqa: E402
from app.db import get_conn, get_pool  # noqa: E402
from app.dashboard import metrics  # noqa: E402

PROJECT_NAME = "In-Store Pickup Experience"

TURNS = [
    # ----- EMPATHIZE ---------------------------------------------------------
    {
        "phase": "empathy", "usage": "synthesis", "evidence": True, "handoff": False,
        "user": (
            "My team at Northwind is about to design an in-store pickup experience. Before we "
            "touch solutions I want us grounded in real shoppers — I've pulled three weeks of "
            "pickup-counter complaints and I'm scheduling ride-alongs with two store associates "
            "this week."
        ),
        "coach": (
            "**Phase 1 — Empathize.** Strong start — you're leading with real evidence "
            "(complaint logs, associate ride-alongs) instead of a hunch, and you're resisting "
            "the urge to design first. As you observe, capture what shoppers *feel* at the "
            "counter, not just what they do."
        ),
        "signals": [
            ("VAL-4", "frames the work around real shoppers, not internal preference"),
            ("VAL-6", "pulled complaint logs and scheduled associate ride-alongs"),
            ("BEH-1", "considers the whole pickup system, counter to back-of-house"),
            ("RES-2", "has three weeks of complaint data to work from"),
        ],
    },
    {
        "phase": "empathy", "usage": "synthesis", "evidence": True, "handoff": False,
        "user": (
            "What I'm hearing is shoppers feel anxious not knowing whether their order is "
            "actually ready, and associates waste time hunting for misplaced bags. I keep "
            "reminding the team to stay in the shopper's shoes rather than jump to building an "
            "app, and I've asked our ops lead to share what she sees from the back."
        ),
        "coach": (
            "**Phase 1 — Empathize.** You've surfaced the real emotional core — uncertainty — "
            "and you're actively pulling in other vantage points (ops) and holding the team in "
            "the shopper's perspective. That's exactly the discipline this phase needs."
        ),
        "signals": [
            ("VAL-7", "keeps the team in the shopper's shoes; names their anxiety"),
            ("CLI-1", "brings in the ops lead's perspective"),
            ("CLI-2", "co-developing the understanding with the team"),
        ],
    },
    # ----- DEFINE ------------------------------------------------------------
    {
        "phase": "define", "usage": "reframing", "evidence": True, "handoff": False,
        "user": (
            "I drafted a problem statement with the team: 'Pickup shoppers need confidence "
            "their order is ready and findable, because uncertainty drives counter anxiety and "
            "wasted associate time.' I pushed back on our first version that just said 'we need "
            "a notification app.'"
        ),
        "coach": (
            "**Phase 2 — Define.** That's a genuine problem statement — user, need, and an "
            "evidence-based insight, with the solution stripped out. Good catch rejecting the "
            "'app' version; that would have locked you in before ideating. Hold this framing.",
        ),
        "signals": [
            ("BEH-3", "reframes away from 'we need an app' to the underlying need"),
            ("BEH-5", "challenges the team's first solution-shaped framing"),
            ("PRO-1", "knows she's defining, not yet solving"),
        ],
    },
    # ----- IDEATE ------------------------------------------------------------
    {
        "phase": "ideate", "usage": "ideation", "evidence": False, "handoff": False,
        "user": (
            "I'll be honest — my own first reaction was to put in a locker system and call it "
            "done, and the team nearly converged on it in five minutes. I caught us and we "
            "instead generated several directions: a ready-state shelf light, an SMS ready-"
            "ping, a staffed concierge handoff, self-service lockers, and a simple numbered-bag "
            "system. I'm bringing in our ops lead and a store associate to weigh in before we "
            "judge any of them."
        ),
        "coach": (
            "**Phase 3 — Ideate.** Two good instincts there: you noticed your own jump to a "
            "solution, and you caught the team converging too fast — then opened it back up to "
            "five real options and invited other disciplines in. That self-awareness is what "
            "keeps ideation honest."
        ),
        "signals": [
            ("BEH-4", "own first reaction was to jump straight to a locker system"),
            ("PRO-9", "team nearly converged on one option in five minutes"),
            ("BEH-7", "reopened to five distinct directions"),
            ("PRO-8", "keeps multiple options open before judging"),
            ("CLI-3", "brings in ops and a store associate across disciplines"),
            ("CLI-7", "treats the cross-discipline input as improving the outcome"),
        ],
    },
    # ----- PROTOTYPE ---------------------------------------------------------
    {
        "phase": "prototype", "usage": "poc-scoping", "evidence": True, "handoff": False,
        "user": (
            "We'll mock the cheapest two — the numbered-bag system and an SMS ready-ping — and "
            "run them at one store for a week to test whether 'findability' is really the core "
            "anxiety. No app build yet."
        ),
        "coach": (
            "**Phase 4 — Prototype.** Right altitude: two low-cost mocks aimed at the riskiest "
            "assumption (that findability is the real driver), at one store, before any build. "
            "Make sure you know what result would change your mind."
        ),
        "signals": [
            ("PRO-7", "turns the ideas into two testable mocks"),
            ("PRO-4", "tests the riskiest assumption in a one-store, one-week step"),
            ("PRO-5", "favours making something concrete over more debate"),
        ],
    },
    # ----- TEST --------------------------------------------------------------
    {
        "phase": "test", "usage": "evidence-check", "evidence": True, "handoff": True,
        "user": (
            "Before the pilot I want clear success criteria — counter wait time down 20% and "
            "'is it ready?' questions cut in half — measured over the week. Honestly my one "
            "worry is I'm tempted to call it a win if associates simply like it, which I know "
            "isn't enough."
        ),
        "coach": (
            "**Phase 5 — Test.** Those are real, measurable criteria set in advance — exactly "
            "right. And naming your own bias (mistaking 'associates liked it' for success) is "
            "how you avoid it. This is a live pilot with real people, so **it's a handoff** — "
            "run it and bring back the numbers."
        ),
        "signals": [
            ("SUC-3", "ties success to measurable criteria (wait time −20%, questions halved)"),
            ("SUC-6", "will validate over a week of real data"),
            ("BEH-6", "pressure-tests her own definition of success"),
            ("SUC-7", "tempted to treat 'associates liked it' as the finish line"),
        ],
    },
    {
        "phase": "test", "usage": "evidence-check", "evidence": True, "handoff": False,
        "user": (
            "Whatever the pilot shows, I want us to treat it as a read on the problem, not a "
            "verdict on the idea — if findability isn't the driver, we reframe rather than "
            "double down. The win I care about is shoppers leaving the counter confident, "
            "tracked over the quarter, not a good demo day."
        ),
        "coach": (
            "**Phase 5 — Test.** That's mature leadership of the process: outcome defined over "
            "a real horizon, results treated as learning, and a willingness to reframe the "
            "problem rather than defend the solution. Model that for the team and it sticks."
        ),
        "signals": [
            ("VAL-9", "ready to reframe rather than double down if she's wrong"),
            ("PRO-10", "foresees outcomes and plans to adapt the direction"),
            ("SUC-2", "articulates the impact: shoppers leaving the counter confident"),
            ("SUC-6", "tracks the outcome over a quarter, not a demo day"),
        ],
    },
]


def seed() -> None:
    with get_conn() as conn:
        maya = conn.execute(
            "SELECT id, org_id, team_id FROM users WHERE email='maya@northwind.com'"
        ).fetchone()
        skill = conn.execute("SELECT id FROM skills WHERE command='design-thinking'").fetchone()
        org_id, maya_id, team_id, skill_id = (
            str(maya["org_id"]), str(maya["id"]), str(maya["team_id"]), str(skill["id"])
        )
        # Clean Maya's prior conversations (cascades her stray interactions/signals) so her
        # own dashboard is fully controlled.
        for r in conn.execute("SELECT id FROM conversations WHERE user_id=%s", (maya_id,)).fetchall():
            conn.execute("DELETE FROM conversations WHERE id=%s", (r["id"],))

        proj = conn.execute(
            "SELECT id FROM projects WHERE owner_kind='user' AND owner_id=%s AND name=%s",
            (maya_id, PROJECT_NAME),
        ).fetchone()
        if not proj:
            proj = conn.execute(
                "INSERT INTO projects (org_id, name, owner_kind, owner_id, created_by) "
                "VALUES (%s,%s,'user',%s,%s) RETURNING id",
                (org_id, PROJECT_NAME, maya_id, maya_id),
            ).fetchone()
        project_id = str(proj["id"])

        title = "/design-thinking · In-store pickup experience"
        start = datetime.now(timezone.utc) - timedelta(days=9)
        conv = conn.execute(
            "INSERT INTO conversations (org_id, user_id, project_id, skill_id, title, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (org_id, maya_id, project_id, skill_id, title, start, start),
        ).fetchone()
        conv_id = str(conv["id"])

        pos = neg = 0
        for i, t in enumerate(TURNS):
            ts = start + timedelta(days=i, minutes=3)
            um = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at) "
                "VALUES (%s,'user',%s,%s) RETURNING id",
                (conv_id, t["user"], ts),
            ).fetchone()
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at) "
                "VALUES (%s,'assistant',%s,%s)",
                (conv_id, t["coach"], ts + timedelta(seconds=20)),
            )
            pcount: dict[str, int] = {}
            tpos = tneg = 0
            for sid, _ in t["signals"]:
                s = BY_ID[sid]
                pcount[s.pillar] = pcount.get(s.pillar, 0) + 1
                tpos += 1 if s.polarity > 0 else 0
                tneg += 1 if s.polarity < 0 else 0
            dom = max(pcount, key=pcount.get) if pcount else None
            ratio = tpos / (tpos + tneg) if (tpos + tneg) else 0.5
            quality = max(1, min(5, round(1 + ratio * 4)))
            inter = conn.execute(
                """
                INSERT INTO interactions
                    (org_id, user_id, conversation_id, message_id, pillar, phase, usage_type,
                     evidence_backed, quality_score, handoff, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                (org_id, maya_id, conv_id, str(um["id"]), dom, t["phase"], t["usage"],
                 t["evidence"], quality, t["handoff"], ts + timedelta(seconds=30)),
            ).fetchone()
            for sid, evidence in t["signals"]:
                s = BY_ID[sid]
                conn.execute(
                    """
                    INSERT INTO interaction_signals
                        (interaction_id, org_id, user_id, signal_id, pillar, polarity, evidence, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (str(inter["id"]), org_id, maya_id, sid, s.pillar, s.polarity, evidence,
                     ts + timedelta(seconds=30)),
                )
                pos += 1 if s.polarity > 0 else 0
                neg += 1 if s.polarity < 0 else 0
        conn.execute("UPDATE conversations SET updated_at=%s WHERE id=%s",
                     (start + timedelta(days=len(TURNS)), conv_id))
        conn.commit()
        print(f"✓ seeded {len(TURNS)} turns ({pos} positive / {neg} anti-signals) for Maya")

    iv = metrics.individual_view(org_id, maya_id, "Maya Lindqvist")
    print("\n=== Maya's own dashboard (My Progress) ===")
    print(f"  DQ {iv['dq_score']}  interactions {iv['total_interactions']}  evidence {iv['evidence_rate']}%")
    for p, s in iv["pillar_scores"].items():
        c = iv["pillar_counts"][p]
        print(f"    {p:<10} {str(s):>6}   (+{c['pos']}/-{c['neg']})")
    print(f"  phases: {iv['phase_counts']}   skipped: {iv['skipped_phases'] or 'none'}")
    tv = metrics.team_view(org_id, team_id, include_members=True)
    print(f"\n=== Team (rolls up Maya + Raj) ===  team DQ {tv['team_dq']}   phases {tv['phase_counts']}")


def main() -> None:
    try:
        seed()
    finally:
        get_pool().close()


if __name__ == "__main__":
    sys.exit(main())
