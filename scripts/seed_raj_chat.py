"""Demo seed: drive a real /design-thinking coaching engagement as Raj Mehta.

This does NOT fabricate dashboard rows. It logs in as the demo employee and sends a
realistic, phase-by-phase design-thinking conversation through the LIVE /chat endpoint —
the same code path the web app uses. The backend generates real coach replies and runs
its real passive tagging, so the resulting interactions + fired signals show up on the
manager dashboard (Maya) exactly as they would from genuine usage.

The conversation content is grounded in a service-design case study on reducing food
waste in Chicago's food-service industry (systems mapping, stakeholder think tanks,
service blueprints) — the "final project" the employee is working through.

Run from the backend dir (so .env / venv resolve):
    cd backend && python ../scripts/seed_raj_chat.py
"""
from __future__ import annotations

import sys
import time

import httpx

BASE = "http://localhost:8000"
RAJ = ("raj@northwind.com", "pulse1234")
PROJECT_NAME = "Chicago Food Waste — Final Project"

# Realistic employee turns with a genuine LEARNING ARC: Raj starts shaky (jumping to a
# solution, leaning on assumptions, converging too early) and the coach corrects him each
# time, so the tagging carries a believable mix of positive and anti-signals across all six
# pillars — scores land in the 80s, not a flawless 90s. The arc walks all five phases, with
# an explicit TEST phase at the end so the phase-habits graph fills out.
TURNS: list[str] = [
    # --- EMPATHIZE -----------------------------------------------------------
    # 1. Opens solution-first (anti: jumps to a build, assumes user reaction, skips empathy).
    "/design-thinking For my final project I want to build a slick web dashboard that shows "
    "Chicago food-service operators their waste data. Honestly I'm pretty sure operators will "
    "love it, so I'd like to jump straight into designing the screens. The project is about "
    "reducing food waste in Chicago before the city launched its first citywide composting "
    "program.",

    # 2. Recovers into real empathy with first-hand evidence.
    "Okay, fair — I'm getting ahead of myself. The people I'm actually designing for are city "
    "officials and policy staff, food-service & retail operators, food-rescue and community "
    "organizations, and food-scrap recyclers. My real evidence is first-hand: we ran the "
    "'Food Matters Think Tank 1.0' convening at the Auburn Gresham Healthy Lifestyle Hub, and "
    "I did one-on-one interviews with city officials.",

    # 3. Empathy depth, but admits a real gap (anti: assumed operator needs, went siloed).
    "The barriers I heard were competing priorities across the supply chain, an inconsistent "
    "flow of data, and one official told me directly 'there's no existing policy on separating "
    "organic waste from solid waste.' I'll be honest though: I went deep with the city but I "
    "haven't actually sat down with the operators themselves yet — I've mostly been assuming "
    "what they need.",

    # --- DEFINE --------------------------------------------------------------
    # 4. Solution-shaped problem statement (anti: solution-in-disguise, premature converge).
    "Here's my problem statement: 'Chicago operators need a centralized waste-data dashboard "
    "so they can track and cut their waste.' That feels right to me — can we lock it in?",

    # 5. Reframes properly and challenges his own assumption.
    "You're right, that's just my solution in disguise. Let me question my own assumption — am "
    "I sure the problem is visibility? Re-reading my notes, the deeper insight is operators "
    "don't act because the cost and effort land on them while the benefit is shared by "
    "everyone. Reframed: 'Food-service operators need diversion to be the low-effort default, "
    "because today they carry the burden while the benefit is diffuse.'",

    # --- IDEATE --------------------------------------------------------------
    # 6. Tries to converge on the first idea again (anti: commits early, wants certainty).
    "Honestly I still think a dashboard is the answer — can we just go with that one and move "
    "on so I'm not wasting time?",

    # 7. Defers judgment, generates breadth, brings in diverse teammates.
    "Alright, deferring judgment. With two teammates we generated distinct directions: (1) a "
    "peer case-study platform; (2) a flexible shared data standard; (3) a recognition and "
    "incentive scheme; (4) a community composting toolkit; (5) a city policy roadmap; (6) a "
    "food-rescue matchmaking service. My policy teammate favours the data standard, the "
    "community-org person favours the toolkit — both views are improving my thinking, so I'm "
    "keeping several alive instead of killing options.",

    # --- PROTOTYPE -----------------------------------------------------------
    # 8. Premature-build temptation (anti: skip ahead, jump to the full solution).
    "Part of me just wants to skip ahead and build the full platform now — it feels obvious "
    "and I'm impatient to have something real.",

    # 9. Recovers: cheapest artifact aimed at the riskiest assumption.
    "Fair, that's me jumping again. Lowest-fidelity instead: I'll make a paper service "
    "blueprint plus a clickable mock of just the 'case-study board.' The riskiest assumption "
    "to test is whether operators would actually share and trust peer data — nothing more than "
    "that.",

    # --- TEST ----------------------------------------------------------------
    # 10. Test plan, but treats launch as the finish line (anti: no validation past the demo).
    "For testing I'll run the 'Food Matters Think Tank 2.0' and put the blueprint in front of "
    "real operators. If they like the demo, I figure we're basically done and can ship it.",

    # 11. Defines success criteria before the test; real users; explicit human handoff.
    "Good point — testing isn't shipping. Before the session I'll define success up front: at "
    "least 3 of 5 operator participants commit to contributing a case study, and we surface "
    "two concrete data-gaps the standard must close. This is real-user testing I shouldn't "
    "simulate — I'll run it live with the operators and measure against those criteria, not "
    "vibes.",

    # 12. Impact + validate-with-evidence over time, learn and adjust.
    "The impact I'm aiming for is aligning city, businesses and community orgs on actionable "
    "strategies — measured by adoption of the data standard and the number of operator-to-"
    "rescue matches over 90 days, not the launch event. I'd rather validate with evidence "
    "after the think tank than declare victory on demo day, and adjust from what we learn in "
    "testing.",
]


def login() -> str:
    r = httpx.post(f"{BASE}/auth/login", json={"email": RAJ[0], "password": RAJ[1]}, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(f"✓ logged in as {data['user']['name']} ({data['user']['role']})")
    return data["token"]


def reset_design_thinking_chats(token: str) -> None:
    """Delete any prior /design-thinking conversations so we don't double-count signals.
    Deleting a conversation cascades its messages, interactions and fired signals."""
    h = {"Authorization": f"Bearer {token}"}
    convos = httpx.get(f"{BASE}/conversations", headers=h, timeout=30).json()
    removed = 0
    for c in convos:
        if c["title"].startswith("/design-thinking"):
            httpx.delete(f"{BASE}/conversations/{c['id']}", headers=h, timeout=30)
            removed += 1
    if removed:
        print(f"✓ cleared {removed} prior design-thinking conversation(s)")


def ensure_project(token: str) -> str:
    """A personal project owned by Raj. The chat sidebar only lists conversations that
    belong to a project, so the seeded chat must live inside one to appear in his history."""
    h = {"Authorization": f"Bearer {token}"}
    for p in httpx.get(f"{BASE}/projects", headers=h, timeout=30).json():
        if p["name"] == PROJECT_NAME:
            print(f"✓ reusing project '{PROJECT_NAME}'")
            return p["id"]
    r = httpx.post(f"{BASE}/projects", json={"name": PROJECT_NAME}, headers=h, timeout=30)
    r.raise_for_status()
    print(f"✓ created project '{PROJECT_NAME}'")
    return r.json()["id"]


def send(token: str, message: str, conversation_id: str | None, project_id: str | None) -> dict:
    form = {"message": message}
    if conversation_id:
        form["conversation_id"] = conversation_id
    elif project_id:  # only on the first turn; afterwards the conversation carries the project
        form["project_id"] = project_id
    r = httpx.post(
        f"{BASE}/chat",
        data=form,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def main() -> None:
    token = login()
    reset_design_thinking_chats(token)
    project_id = ensure_project(token)
    conversation_id: str | None = None
    for i, msg in enumerate(TURNS, 1):
        phase_hint = msg[:60].replace("\n", " ")
        for attempt in range(4):
            try:
                res = send(token, msg, conversation_id, project_id)
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 5:
                    wait = (attempt + 1) * 20
                    print(f"  · rate-limited, backing off {wait}s…")
                    time.sleep(wait)
                    continue
                raise
        conversation_id = res["conversation_id"]
        tag = res.get("tag") or {}
        fired = tag.get("fired_signals") or []
        sig_str = ", ".join(
            f"{s['id']}{'+' if s['polarity'] > 0 else '−'}" for s in fired
        ) or "(none)"
        print(
            f"[{i:>2}/{len(TURNS)}] phase={tag.get('phase', '?'):<9} "
            f"signals: {sig_str}"
        )
        # Generous spacing to stay under the free Gemini tier's per-minute limit
        # (each turn already costs an embed + a generate + a tag call).
        time.sleep(15)

    print(f"\n✓ done — conversation {conversation_id}")
    print("  Raj now has a real /design-thinking engagement; Maya's dashboard reflects it.")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as e:
        print(f"HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
