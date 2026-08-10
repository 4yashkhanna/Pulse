"""Passive tagging — turns a conversation turn into dashboard data (org-scoped).

The tagger no longer guesses a single 1-5 quality number. It returns the list of
behavioural SIGNALS that fired in the user's turn (see signals.py). Each fired signal is
stored as an audit row, and pillar scores are computed from positives vs. anti-signals.
The phase / usage_type / evidence / handoff fields are kept for the chat UI and filters.
"""
from __future__ import annotations

from ..config import DT_PHASES, USAGE_TYPES
from ..db import get_conn
from ..llm import generate_json
from .signals import ALL_IDS, BY_ID, PILLARS, prompt_catalog

TAG_SYSTEM = f"""You are a silent analyst for KPMG's Design Intelligence Coach. Given one \
turn of a coaching conversation, judge the USER's thinking (not the coach's reply) against \
a fixed catalogue of behavioural signals.

Return JSON with:
- phase: which design-thinking phase the user is in. One of: {DT_PHASES}.
- usage_type: what the user is using the coach for. One of: {USAGE_TYPES}.
- evidence_backed: true if the user grounds a decision in real evidence; false if assumption/instinct.
- handoff: true if the right next step is real human work (field observation, real user \
testing, ethical/stakeholder judgment) that AI should not simulate.
- fired_signals: the signals CLEARLY present in this turn. For each, give:
    - id: the signal id (only include a signal if the user's words genuinely demonstrate it — do not guess)
    - evidence: a SHORT (max ~20 words) direct quote or tight paraphrase of what the USER said \
that demonstrates this signal. This is the human-readable reason, so make it concrete and specific \
to what they actually wrote.
  Most turns fire 1-4 signals.

SIGNAL CATALOGUE (id (+/-): meaning):
{prompt_catalog()}"""

TAG_SCHEMA = {
    "type": "object",
    "properties": {
        "phase": {"type": "string", "enum": DT_PHASES},
        "usage_type": {"type": "string", "enum": USAGE_TYPES},
        "evidence_backed": {"type": "boolean"},
        "handoff": {"type": "boolean"},
        "fired_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "enum": ALL_IDS},
                    "evidence": {"type": "string"},
                },
                "required": ["id", "evidence"],
            },
        },
    },
    "required": ["phase", "usage_type", "evidence_backed", "handoff", "fired_signals"],
}


def classify(user_message: str, coach_reply: str) -> dict:
    content = f"USER TURN:\n{user_message}\n\nCOACH REPLY:\n{coach_reply}"
    raw = generate_json(TAG_SYSTEM, content, TAG_SCHEMA)
    return _sanitize(raw)


def _sanitize(raw: dict) -> dict:
    phase = raw.get("phase") if raw.get("phase") in DT_PHASES else "define"
    usage = raw.get("usage_type") if raw.get("usage_type") in USAGE_TYPES else "ideation"
    fired: list[dict] = []
    seen: set[str] = set()
    for item in raw.get("fired_signals") or []:
        if isinstance(item, dict):
            sid = item.get("id")
            ev = (item.get("evidence") or "").strip()
        else:  # tolerate a bare id
            sid, ev = item, ""
        if sid in BY_ID and sid not in seen:
            seen.add(sid)
            fired.append({"id": sid, "evidence": ev[:240]})
    return {
        "phase": phase,
        "usage_type": usage,
        "evidence_backed": bool(raw.get("evidence_backed", False)),
        "handoff": bool(raw.get("handoff", False)),
        "fired_signals": fired,
    }


def _derive_pillar_and_quality(fired: list[dict]) -> tuple[str | None, int]:
    """Back-compat fields for the interactions row: the dominant pillar touched and a
    coarse 1-5 quality from the positive/negative ratio of fired signals."""
    if not fired:
        return None, 3
    pillar_counts: dict[str, int] = {}
    pos = neg = 0
    for item in fired:
        s = BY_ID[item["id"]]
        pillar_counts[s.pillar] = pillar_counts.get(s.pillar, 0) + 1
        if s.polarity > 0:
            pos += 1
        else:
            neg += 1
    pillar = max(pillar_counts, key=pillar_counts.get)
    ratio = pos / (pos + neg) if (pos + neg) else 0.5
    quality = max(1, min(5, round(1 + ratio * 4)))
    return pillar, quality


def tag_and_store(
    *,
    org_id: str,
    user_id: str,
    conversation_id: str,
    message_id: str,
    user_message: str,
    coach_reply: str,
) -> dict:
    tag = classify(user_message, coach_reply)
    fired = tag["fired_signals"]
    pillar, quality = _derive_pillar_and_quality(fired)

    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO interactions
                (org_id, user_id, conversation_id, message_id, pillar, phase, usage_type,
                 evidence_backed, quality_score, handoff)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """,
            (
                org_id, user_id, conversation_id, message_id, pillar,
                tag["phase"], tag["usage_type"], tag["evidence_backed"], quality, tag["handoff"],
            ),
        ).fetchone()
        interaction_id = str(row["id"])
        for item in fired:
            s = BY_ID[item["id"]]
            conn.execute(
                """
                INSERT INTO interaction_signals
                    (interaction_id, org_id, user_id, signal_id, pillar, polarity, evidence)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (interaction_id, org_id, user_id, item["id"], s.pillar, s.polarity, item["evidence"]),
            )
        conn.commit()

    # Build the explainable payload for the chat UI.
    return {
        "phase": tag["phase"],
        "usage_type": tag["usage_type"],
        "evidence_backed": tag["evidence_backed"],
        "handoff": tag["handoff"],
        "pillar": pillar,
        "quality_score": quality,
        "fired_signals": [
            {
                "id": item["id"],
                "pillar": BY_ID[item["id"]].pillar,
                "polarity": BY_ID[item["id"]].polarity,
                "text": BY_ID[item["id"]].text,
                "evidence": item["evidence"],
            }
            for item in fired
        ],
    }
