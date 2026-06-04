"""Dashboard metrics — scored from fired signals (interaction_signals), org-scoped.

Pillar score = positives / (positives + negatives) of the fired signals for that pillar,
on a 0-100 scale. A pillar with fewer than MIN_EVIDENCE fired signals returns None
("not enough data yet") rather than a misleading number. DQ is the weighted blend of the
pillars that DO have data (weights renormalised over those). No AI here — pure arithmetic.
"""
from __future__ import annotations

from ..config import DT_PHASES, PILLAR_WEIGHTS
from ..coach.signals import BY_ID, PILLARS
from ..db import get_conn

MIN_EVIDENCE = 3


def _signal_counts(where: str, params: tuple) -> dict[str, dict[str, int]]:
    """{pillar: {'pos': p, 'neg': n}} from interaction_signals."""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT pillar,
                   SUM(CASE WHEN polarity > 0 THEN 1 ELSE 0 END) AS pos,
                   SUM(CASE WHEN polarity < 0 THEN 1 ELSE 0 END) AS neg
            FROM interaction_signals WHERE {where} GROUP BY pillar
            """,
            params,
        ).fetchall()
    out = {p: {"pos": 0, "neg": 0} for p in PILLARS}
    for r in rows:
        if r["pillar"] in out:
            out[r["pillar"]] = {"pos": int(r["pos"] or 0), "neg": int(r["neg"] or 0)}
    return out


def _pillar_scores(counts: dict[str, dict[str, int]]) -> dict[str, float | None]:
    scores: dict[str, float | None] = {}
    for p in PILLARS:
        pos, neg = counts[p]["pos"], counts[p]["neg"]
        n = pos + neg
        scores[p] = round(pos / n * 100, 1) if n >= MIN_EVIDENCE else None
    return scores


def dq_score(scores: dict[str, float | None]) -> float | None:
    active = {p: s for p, s in scores.items() if s is not None}
    if not active:
        return None
    total_w = sum(PILLAR_WEIGHTS[p] for p in active)
    return round(sum(scores[p] * PILLAR_WEIGHTS[p] for p in active) / total_w, 1)


def _breakdown(where: str, params: tuple) -> dict[str, list[dict]]:
    """Per pillar, the fired signals with counts AND a concrete recent quote — the
    human-readable 'because…' behind every score."""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT pillar, signal_id, polarity, COUNT(*) AS n,
                   (array_agg(evidence ORDER BY created_at DESC)
                      FILTER (WHERE evidence IS NOT NULL AND evidence <> ''))[1] AS example
            FROM interaction_signals WHERE {where}
            GROUP BY pillar, signal_id, polarity ORDER BY n DESC
            """,
            params,
        ).fetchall()
    out: dict[str, list[dict]] = {p: [] for p in PILLARS}
    for r in rows:
        sid = r["signal_id"]
        if r["pillar"] in out:
            out[r["pillar"]].append(
                {
                    "signal_id": sid,
                    "polarity": int(r["polarity"]),
                    "count": int(r["n"]),
                    "text": BY_ID[sid].text if sid in BY_ID else sid,
                    "example": r["example"],
                }
            )
    return out


def _phase_counts(where: str, params: tuple) -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT phase, COUNT(*) AS n FROM interactions WHERE {where} GROUP BY phase", params
        ).fetchall()
    counts = {ph: 0 for ph in DT_PHASES}
    for r in rows:
        if r["phase"] in counts:
            counts[r["phase"]] = int(r["n"])
    return counts


def _totals(where: str, params: tuple) -> dict:
    with get_conn() as conn:
        r = conn.execute(
            f"""
            SELECT COUNT(*) AS n,
                   AVG(CASE WHEN evidence_backed THEN 1.0 ELSE 0.0 END) AS evidence_rate
            FROM interactions WHERE {where}
            """,
            params,
        ).fetchone()
    return {
        "total_interactions": int(r["n"] or 0),
        "evidence_rate": round(float(r["evidence_rate"] or 0) * 100, 1),
    }


def _baseline(org_id: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT pillar, score FROM baseline WHERE org_id = %s AND scope = 'org'", (org_id,)
        ).fetchall()
    if not rows:
        return {"baseline_dq": None, "baseline_pillar_scores": {}}
    bp = {r["pillar"]: float(r["score"]) for r in rows}
    full = {**{p: 0.0 for p in PILLARS}, **bp}
    return {"baseline_dq": dq_score(full), "baseline_pillar_scores": bp}


# --------------------------------------------------------------------------- #
def individual_view(org_id: str, user_id: str, name: str | None = None) -> dict:
    sig_where, sig_params = "org_id = %s AND user_id = %s", (org_id, user_id)
    int_where, int_params = "org_id = %s AND user_id = %s", (org_id, user_id)

    counts = _signal_counts(sig_where, sig_params)
    scores = _pillar_scores(counts)
    phases = _phase_counts(int_where, int_params)
    with get_conn() as conn:
        usage = conn.execute(
            "SELECT usage_type, COUNT(*) AS n FROM interactions WHERE org_id=%s AND user_id=%s GROUP BY usage_type",
            (org_id, user_id),
        ).fetchall()
    return {
        "name": name,
        "pillar_scores": scores,
        "pillar_counts": counts,
        "breakdown": _breakdown(sig_where, sig_params),
        "dq_score": dq_score(scores),
        "phase_counts": phases,
        "skipped_phases": [ph for ph, n in phases.items() if n == 0],
        "usage_breakdown": {r["usage_type"]: int(r["n"]) for r in usage},
        **_totals(int_where, int_params),
        **_baseline(org_id),
    }


def team_view(org_id: str, team_id: str, *, include_members: bool) -> dict:
    with get_conn() as conn:
        members = conn.execute(
            "SELECT id, name FROM users WHERE org_id = %s AND team_id = %s ORDER BY name",
            (org_id, team_id),
        ).fetchall()
        team = conn.execute("SELECT name FROM teams WHERE id = %s", (team_id,)).fetchone()
    member_ids = [str(m["id"]) for m in members]

    if member_ids:
        sig_where, sig_params = "org_id = %s AND user_id = ANY(%s)", (org_id, member_ids)
        counts = _signal_counts(sig_where, sig_params)
        scores = _pillar_scores(counts)
        phases = _phase_counts("org_id = %s AND user_id = ANY(%s)", (org_id, member_ids))
        totals = _totals("org_id = %s AND user_id = ANY(%s)", (org_id, member_ids))
        breakdown = _breakdown(sig_where, sig_params)
    else:
        counts = {p: {"pos": 0, "neg": 0} for p in PILLARS}
        scores = {p: None for p in PILLARS}
        phases = {ph: 0 for ph in DT_PHASES}
        totals = {"total_interactions": 0, "evidence_rate": 0}
        breakdown = {p: [] for p in PILLARS}

    result = {
        "team_name": team["name"] if team else "Team",
        "team_dq": dq_score(scores),
        "team_pillar_scores": scores,
        "breakdown": breakdown,
        "phase_counts": phases,
        "most_skipped_phase": min(phases, key=phases.get) if phases else None,
        **totals,
    }
    if include_members:
        result["members"] = [
            {
                "id": str(m["id"]),
                "name": m["name"],
                **{
                    k: v
                    for k, v in individual_view(org_id, str(m["id"]), m["name"]).items()
                    if k in ("dq_score", "pillar_scores", "total_interactions")
                },
            }
            for m in members
        ]
    return result
