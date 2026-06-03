"""Passive tagging — the AI job that turns a conversation turn into dashboard data.

Classifies each user turn against the 6 pillars, the DT phase, usage type, whether
the decision was evidence-backed, a quality (sophistication) score, and whether a human
handoff was warranted. Writes one row to `interactions`. In production this runs batched
on a timer; in the prototype it runs synchronously so the DQ score moves live.
"""
from __future__ import annotations

from ..config import DT_PHASES, PILLAR_WEIGHTS, USAGE_TYPES
from ..db import get_conn
from ..llm import generate_json

PILLARS = list(PILLAR_WEIGHTS.keys())

TAG_SYSTEM = f"""You are a silent analyst for KPMG's Design Intelligence Coach. Given one \
turn of a coaching conversation, classify it for a design-maturity dashboard. Judge the \
sophistication of the USER's thinking, not the coach's reply.

Return JSON with exactly these fields:
- pillar: which design-maturity pillar the turn most touches. One of: {PILLARS}.
- phase: which design-thinking phase the user is in. One of: {DT_PHASES}.
- usage_type: what the user is using the coach for. One of: {USAGE_TYPES}.
- evidence_backed: true if the user is grounding a decision in real evidence (data, \
research, user observation); false if working from assumption or instinct.
- quality_score: integer 1-5. 1 = jumping to solutions / pure assumption. 3 = competent. \
5 = rigorous, evidence-seeking, pressure-tests own assumptions.
- handoff: true if the right next step is real human work (field observation, real user \
testing, ethical/stakeholder judgment) that AI should not simulate."""

TAG_SCHEMA = {
    "type": "object",
    "properties": {
        "pillar": {"type": "string", "enum": PILLARS},
        "phase": {"type": "string", "enum": DT_PHASES},
        "usage_type": {"type": "string", "enum": USAGE_TYPES},
        "evidence_backed": {"type": "boolean"},
        "quality_score": {"type": "integer"},
        "handoff": {"type": "boolean"},
    },
    "required": ["pillar", "phase", "usage_type", "evidence_backed", "quality_score", "handoff"],
}


def classify(user_message: str, coach_reply: str) -> dict:
    content = f"USER TURN:\n{user_message}\n\nCOACH REPLY:\n{coach_reply}"
    raw = generate_json(TAG_SYSTEM, content, TAG_SCHEMA)
    return _sanitize(raw)


def _sanitize(raw: dict) -> dict:
    pillar = raw.get("pillar") if raw.get("pillar") in PILLARS else "process"
    phase = raw.get("phase") if raw.get("phase") in DT_PHASES else "define"
    usage = raw.get("usage_type") if raw.get("usage_type") in USAGE_TYPES else "ideation"
    try:
        quality = int(raw.get("quality_score", 3))
    except (TypeError, ValueError):
        quality = 3
    quality = max(1, min(5, quality))
    return {
        "pillar": pillar,
        "phase": phase,
        "usage_type": usage,
        "evidence_backed": bool(raw.get("evidence_backed", False)),
        "quality_score": quality,
        "handoff": bool(raw.get("handoff", False)),
    }


def tag_and_store(
    *,
    conversation_id: str,
    message_id: str,
    user_id: str,
    user_message: str,
    coach_reply: str,
) -> dict:
    tag = classify(user_message, coach_reply)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO interactions
                (conversation_id, message_id, user_id, pillar, phase, usage_type,
                 evidence_backed, quality_score, handoff)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                conversation_id,
                message_id,
                user_id,
                tag["pillar"],
                tag["phase"],
                tag["usage_type"],
                tag["evidence_backed"],
                tag["quality_score"],
                tag["handoff"],
            ),
        )
        conn.commit()
    return tag
