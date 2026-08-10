"""Deterministic demo seed: Raj Mehta's /design-thinking engagement on his final project.

Why this exists alongside seed_raj_chat.py: that script drives the LIVE coach (real Gemini
replies + real passive tagging). On the free Gemini tier the daily quota runs out quickly,
which blocks a full 12-turn engagement. This script writes the SAME conversation
deterministically — real conversation + messages (so it shows in Raj's chat history exactly
like a normal chat) plus the interactions and fired signals the tagger would have produced —
without spending any API calls. The signal map is hand-tuned to a realistic learning arc:
Raj starts shaky (jumps to a solution, leans on assumptions, converges early), the coach
corrects him, and he improves. Pillar scores land in the 80s (not a flawless 90s) and all
five design-thinking phases are exercised so the phase-habits graph fills out.

When the Gemini quota resets you can instead run scripts/seed_raj_chat.py to regenerate the
exact same engagement through the real pipeline.

Run from the backend dir:  cd backend && python ../scripts/seed_raj_chat_direct.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db import get_conn, get_pool  # noqa: E402
from app.dashboard import metrics  # noqa: E402

PROJECT_NAME = "Chicago Food Waste — Final Project"

# Each turn: the user's message, an authored coach reply (Design-Thinking-skill voice),
# the passive-measurement fields, and the signals that fire — each with the short evidence
# quote the dashboard shows as the "because…" behind the score. Polarity comes from the
# signal catalogue (app/coach/signals.py), so the map below only lists ids + evidence.
TURNS = [
    # ----- EMPATHIZE ---------------------------------------------------------
    {
        "phase": "empathy", "usage": "ideation", "evidence": False, "handoff": False,
        "user": (
            "For my final project I want to build a slick web dashboard that shows Chicago "
            "food-service operators their waste data. Honestly I'm pretty sure operators will "
            "love it, so I'd like to jump straight into designing the screens. The project is "
            "about reducing food waste in Chicago before the city launched its first citywide "
            "composting program."
        ),
        "coach": (
            "**Phase 1 — Empathize.** Hold on — you've jumped to a solution (a dashboard) and "
            "to an assumption (operators will love it) before we know who these operators are "
            "or what they actually struggle with. That's the most common way design work goes "
            "wrong. Before any screens: who exactly are the people in this system, and what "
            "real evidence do you have about their needs — observation, interviews, data?"
        ),
        "signals": [
            ("VAL-5", "I'm pretty sure operators will love it"),
            ("BEH-4", "wants to jump straight into designing the screens"),
            ("PRO-3", "skips empathy/define and goes straight to a solution"),
        ],
    },
    {
        "phase": "empathy", "usage": "synthesis", "evidence": True, "handoff": False,
        "user": (
            "Okay, fair — I'm getting ahead of myself. The people I'm actually designing for "
            "are city officials and policy staff, food-service & retail operators, food-rescue "
            "and community organizations, and food-scrap recyclers. My real evidence is "
            "first-hand: we ran the 'Food Matters Think Tank 1.0' convening at the Auburn "
            "Gresham Healthy Lifestyle Hub, and I did one-on-one interviews with city officials."
        ),
        "coach": (
            "**Phase 1 — Empathize.** Much better — now you're grounded in real people and "
            "first-hand evidence rather than a hunch. You've named four distinct stakeholder "
            "groups and you've actually convened them. Next, go one level deeper: for each "
            "group, what did you hear in their own words about what gets in their way?"
        ),
        "signals": [
            ("VAL-4", "designing for real stakeholders, not internal preference"),
            ("VAL-6", "ran the Food Matters Think Tank 1.0 and interviewed city officials"),
            ("VAL-7", "frames the work around the different stakeholder groups' needs"),
            ("BEH-1", "considers the whole stakeholder system, not one slice"),
            ("RES-2", "has first-hand convening + interview data to draw on"),
        ],
    },
    {
        "phase": "empathy", "usage": "synthesis", "evidence": True, "handoff": False,
        "user": (
            "The barriers I heard were competing priorities across the supply chain, an "
            "inconsistent flow of data, and one official told me directly 'there's no existing "
            "policy on separating organic waste from solid waste.' I'll be honest though: I "
            "went deep with the city but I haven't actually sat down with the operators "
            "themselves yet — I've mostly been assuming what they need."
        ),
        "coach": (
            "**Phase 1 — Empathize.** That honesty is exactly the right instinct — and it "
            "flags a real gap. You have rich evidence from the city side but you're "
            "assumption-led on the operators, who are the people your solution would actually "
            "land on. Before you define the problem, plan even two short operator "
            "conversations. What's the cheapest way to hear from a few of them this week?"
        ),
        "signals": [
            ("VAL-8", "treats the gap as something to learn, names it openly"),
            ("RES-2", "references the inconsistent flow of data between city and operators"),
            ("CLI-4", "went deep with the city but worked in a silo from the operators"),
        ],
    },
    # ----- DEFINE ------------------------------------------------------------
    {
        "phase": "define", "usage": "reframing", "evidence": False, "handoff": False,
        "user": (
            "Here's my problem statement: 'Chicago operators need a centralized waste-data "
            "dashboard so they can track and cut their waste.' That feels right to me — can "
            "we lock it in?"
        ),
        "coach": (
            "**Phase 2 — Define.** Not yet — that statement has your solution baked into it. "
            "'Need a dashboard' is an answer, not a need. Strip the solution out and write it "
            "as: [user] needs [need] because [insight from your evidence]. What's the "
            "underlying need a dashboard was supposed to serve?"
        ),
        "signals": [
            ("PRO-9", "wants to lock in the first framing prematurely"),
        ],
    },
    {
        "phase": "define", "usage": "reframing", "evidence": True, "handoff": False,
        "user": (
            "You're right, that's just my solution in disguise. Let me question my own "
            "assumption — am I sure the problem is visibility? Re-reading my notes, the deeper "
            "insight is operators don't act because the cost and effort land on them while the "
            "benefit is shared by everyone. Reframed: 'Food-service operators need diversion "
            "to be the low-effort default, because today they carry the burden while the "
            "benefit is diffuse.'"
        ),
        "coach": (
            "**Phase 2 — Define.** That's a real problem statement now — it names the user, a "
            "genuine need (low-effort default), and an insight grounded in your evidence (the "
            "burden/benefit mismatch). It's also testable. Hold this framing as we move into "
            "ideation; don't let the first solution sneak back in."
        ),
        "signals": [
            ("VAL-7", "sees the problem from the operators' burden/benefit perspective"),
            ("VAL-8", "re-reads notes to learn a deeper insight"),
            ("BEH-3", "reframes — 'that's my solution in disguise'"),
            ("BEH-5", "questions his own assumption that the problem is visibility"),
            ("BEH-6", "pressure-tests his own claim before committing"),
            ("PRO-1", "knows he's in the define phase, holds it before ideating"),
        ],
    },
    # ----- IDEATE ------------------------------------------------------------
    {
        "phase": "ideate", "usage": "ideation", "evidence": False, "handoff": False,
        "user": (
            "Honestly I still think a dashboard is the answer — can we just go with that one "
            "and move on so I'm not wasting time?"
        ),
        "coach": (
            "**Phase 3 — Ideate.** I hear the time pressure, but committing to the first idea "
            "is how you miss the better one. Ideation is cheap; building the wrong thing is "
            "expensive. Give me at least five genuinely different directions before we judge "
            "any of them — defer judgment for now."
        ),
        "signals": [
            ("VAL-2", "wants certainty / one answer to avoid 'wasting time'"),
        ],
    },
    {
        "phase": "ideate", "usage": "ideation", "evidence": True, "handoff": False,
        "user": (
            "Alright, deferring judgment. With two teammates we generated distinct directions: "
            "(1) a peer case-study platform; (2) a flexible shared data standard; (3) a "
            "recognition and incentive scheme; (4) a community composting toolkit; (5) a city "
            "policy roadmap; (6) a food-rescue matchmaking service. My policy teammate favours "
            "the data standard, the community-org person favours the toolkit — both views are "
            "improving my thinking, so I'm keeping several alive instead of killing options."
        ),
        "coach": (
            "**Phase 3 — Ideate.** Now that's breadth — six distinct directions, generated "
            "with people from different vantage points, and you're holding them open instead "
            "of converging. That's exactly the mindset this phase needs. When you're ready, "
            "we'll choose which one or two to prototype based on which assumption is riskiest."
        ),
        "signals": [
            ("VAL-1", "comfortable keeping the problem open, options alive"),
            ("BEH-7", "generated six distinct alternative directions"),
            ("PRO-8", "keeps multiple options open simultaneously"),
            ("CLI-1", "generated the options with two teammates"),
            ("CLI-2", "co-developing the ideas with the team"),
            ("CLI-3", "brought in policy and community-org perspectives"),
            ("CLI-7", "treats the diverse views as improving the outcome"),
        ],
    },
    # ----- PROTOTYPE ---------------------------------------------------------
    {
        "phase": "prototype", "usage": "poc-scoping", "evidence": False, "handoff": False,
        "user": (
            "Part of me just wants to skip ahead and build the full platform now — it feels "
            "obvious and I'm impatient to have something real."
        ),
        "coach": (
            "**Phase 4 — Prototype.** That impatience is normal, but a full build is the most "
            "expensive way to learn you were wrong. The goal of a prototype is to test the "
            "riskiest assumption as cheaply as possible. What's the single assumption that, if "
            "false, sinks the whole idea — and what's the smallest artifact that tests it?"
        ),
        "signals": [],  # a brief impatient aside the coach redirects; nothing firm to tag
    },
    {
        "phase": "prototype", "usage": "poc-scoping", "evidence": True, "handoff": False,
        "user": (
            "Fair, that's me jumping again. Lowest-fidelity instead: I'll make a paper service "
            "blueprint plus a clickable mock of just the 'case-study board.' The riskiest "
            "assumption to test is whether operators would actually share and trust peer data "
            "— nothing more than that."
        ),
        "coach": (
            "**Phase 4 — Prototype.** That's the right altitude: a paper blueprint and a "
            "single clickable mock, aimed squarely at the trust-and-sharing assumption. You're "
            "making something concrete instead of debating it, and you've kept the fidelity "
            "low. Next, who do you put it in front of, and how will you know if the assumption "
            "holds?"
        ),
        "signals": [
            ("VAL-1", "comfortable testing one assumption and leaving the rest open"),
            ("PRO-7", "turns the idea into a testable blueprint + clickable mock"),
            ("PRO-4", "tests the riskiest assumption in a small step"),
            ("PRO-5", "favours making something concrete over more discussion"),
        ],
    },
    # ----- TEST --------------------------------------------------------------
    {
        "phase": "test", "usage": "poc-scoping", "evidence": False, "handoff": False,
        "user": (
            "For testing I'll run the 'Food Matters Think Tank 2.0' and put the blueprint in "
            "front of real operators. If they like the demo, I figure we're basically done and "
            "can ship it."
        ),
        "coach": (
            "**Phase 5 — Test.** Putting it in front of real operators is exactly right — but "
            "'they liked it' isn't a result, and a demo isn't a finish line. Define what "
            "success looks like *before* the session, in terms you can measure, so the test "
            "can actually fail. What would have to happen for you to trust the idea?"
        ),
        "signals": [
            ("PRO-1", "plans the test as a distinct Think Tank 2.0 session"),
            ("SUC-7", "treats a good demo as the finish line — 'basically done, ship it'"),
        ],
    },
    {
        "phase": "test", "usage": "evidence-check", "evidence": True, "handoff": True,
        "user": (
            "Good point — testing isn't shipping. Before the session I'll define success up "
            "front: at least 3 of 5 operator participants commit to contributing a case study, "
            "and we surface two concrete data-gaps the standard must close. This is real-user "
            "testing I shouldn't simulate — I'll run it live with the operators and measure "
            "against those criteria, not vibes."
        ),
        "coach": (
            "**Phase 5 — Test.** That's a real test plan: measurable success criteria set in "
            "advance, with real users, and you're right that this is human fieldwork I "
            "shouldn't fake for you. **This is a handoff** — go run the live session with the "
            "operators. Bring back what you learn and we'll decide whether to iterate the "
            "prototype or the problem framing."
        ),
        "signals": [
            ("VAL-6", "will run the test live with real operators rather than simulate"),
            ("PRO-1", "sets success criteria before the session"),
            ("SUC-3", "ties success to measurable outcomes (3 of 5 commit; two data-gaps)"),
            ("SUC-6", "will validate against criteria, not 'vibes'"),
        ],
    },
    {
        "phase": "test", "usage": "evidence-check", "evidence": True, "handoff": False,
        "user": (
            "The impact I'm aiming for is aligning city, businesses and community orgs on "
            "actionable strategies — measured by adoption of the data standard and the number "
            "of operator-to-rescue matches over 90 days, not the launch event. I'd rather "
            "validate with evidence after the think tank than declare victory on demo day, and "
            "adjust from what we learn in testing."
        ),
        "coach": (
            "**Phase 5 — Test.** This is mature design thinking: you've articulated the impact "
            "you're after, tied it to measurable signals over a real horizon, and you're "
            "treating launch as the start of learning rather than the end. Carry this same "
            "evidence-first discipline into the next iteration — you've come a long way from "
            "'let's just build the dashboard.'"
        ),
        "signals": [
            ("VAL-9", "open to adjusting from what testing reveals"),
            ("PRO-10", "foresees outcomes and plans to adapt the direction"),
            ("SUC-2", "articulates the impact: aligning city, business, community orgs"),
            ("SUC-6", "validates with 90-day evidence rather than declaring victory at launch"),
        ],
    },
]


def _ids(conn) -> tuple[str, str, str, str, str]:
    raj = conn.execute("SELECT id, org_id, team_id FROM users WHERE email='raj@northwind.com'").fetchone()
    skill = conn.execute("SELECT id FROM skills WHERE command='design-thinking'").fetchone()
    proj = conn.execute(
        "SELECT id FROM projects WHERE owner_kind='user' AND owner_id=%s AND name=%s",
        (raj["id"], PROJECT_NAME),
    ).fetchone()
    if not proj:
        proj = conn.execute(
            "INSERT INTO projects (org_id, name, owner_kind, owner_id, created_by) "
            "VALUES (%s,%s,'user',%s,%s) RETURNING id",
            (raj["org_id"], PROJECT_NAME, raj["id"], raj["id"]),
        ).fetchone()
        print(f"✓ created project '{PROJECT_NAME}'")
    else:
        print(f"✓ reusing project '{PROJECT_NAME}'")
    return str(raj["id"]), str(raj["org_id"]), str(raj["team_id"]), str(skill["id"]), str(proj["id"])


def _cleanup(conn, raj_id: str) -> None:
    """Remove prior design-thinking chats and any empty probe conversations (cascades
    messages, interactions and fired signals)."""
    rows = conn.execute(
        """
        SELECT c.id FROM conversations c
        WHERE c.user_id = %s
          AND (c.title LIKE '/design-thinking%%'
               OR NOT EXISTS (SELECT 1 FROM messages m WHERE m.conversation_id = c.id))
        """,
        (raj_id,),
    ).fetchall()
    for r in rows:
        conn.execute("DELETE FROM conversations WHERE id = %s", (r["id"],))
    if rows:
        print(f"✓ cleared {len(rows)} prior/empty conversation(s)")


def seed() -> None:
    from app.coach.signals import BY_ID

    with get_conn() as conn:
        raj_id, org_id, team_id, skill_id, project_id = _ids(conn)
        _cleanup(conn, raj_id)

        title = "/design-thinking · For my final project I want to build…"
        # Spread the engagement over the last ~12 days so it reads like real, paced usage.
        start = datetime.now(timezone.utc) - timedelta(days=12)
        conv = conn.execute(
            "INSERT INTO conversations (org_id, user_id, project_id, skill_id, title, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (org_id, raj_id, project_id, skill_id, title, start, start),
        ).fetchone()
        conv_id = str(conv["id"])

        pos = neg = 0
        for i, t in enumerate(TURNS):
            ts = start + timedelta(days=i, minutes=2)
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
            # Back-compat fields on the interaction row: dominant pillar + coarse quality.
            pcount: dict[str, int] = {}
            tpos = tneg = 0
            for sid, _ in t["signals"]:
                s = BY_ID[sid]
                pcount[s.pillar] = pcount.get(s.pillar, 0) + 1
                if s.polarity > 0:
                    tpos += 1
                else:
                    tneg += 1
            dom_pillar = max(pcount, key=pcount.get) if pcount else None
            ratio = tpos / (tpos + tneg) if (tpos + tneg) else 0.5
            quality = max(1, min(5, round(1 + ratio * 4)))
            inter = conn.execute(
                """
                INSERT INTO interactions
                    (org_id, user_id, conversation_id, message_id, pillar, phase, usage_type,
                     evidence_backed, quality_score, handoff, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
                """,
                (org_id, raj_id, conv_id, str(um["id"]), dom_pillar, t["phase"], t["usage"],
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
                    (str(inter["id"]), org_id, raj_id, sid, s.pillar, s.polarity, evidence,
                     ts + timedelta(seconds=30)),
                )
                pos += 1 if s.polarity > 0 else 0
                neg += 1 if s.polarity < 0 else 0
        conn.execute("UPDATE conversations SET updated_at = %s WHERE id = %s",
                     (start + timedelta(days=len(TURNS)), conv_id))
        conn.commit()
        print(f"✓ seeded {len(TURNS)} turns ({pos} positive / {neg} anti-signals) in conversation {conv_id}")

    # Report the resulting dashboard exactly as Maya will see it.
    iv = metrics.individual_view(org_id, raj_id, "Raj Mehta")
    print("\n=== Raj's dashboard (what Maya drills into) ===")
    print(f"  DQ {iv['dq_score']}  (baseline {iv['baseline_dq']})   interactions {iv['total_interactions']}   evidence {iv['evidence_rate']}%")
    for p, s in iv["pillar_scores"].items():
        c = iv["pillar_counts"][p]
        print(f"    {p:<10} {str(s):>6}   (+{c['pos']}/-{c['neg']})")
    print(f"  phases: {iv['phase_counts']}   skipped: {iv['skipped_phases'] or 'none'}")
    tv = metrics.team_view(org_id, team_id, include_members=True)
    print(f"\n=== Team (Maya) ===  team DQ {tv['team_dq']}   most-skipped {tv['most_skipped_phase']}")


def main() -> None:
    try:
        seed()
    finally:
        get_pool().close()


if __name__ == "__main__":
    sys.exit(main())
