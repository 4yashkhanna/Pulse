"""Dashboard metrics — pure arithmetic over `interactions`, scoped to one org."""
from __future__ import annotations

from ..config import DT_PHASES, PILLAR_WEIGHTS
from ..db import get_conn

PILLARS = list(PILLAR_WEIGHTS.keys())


def _pillar_scores(where: str, params: tuple) -> dict[str, float]:
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT pillar, AVG(quality_score) AS avg_q FROM interactions WHERE {where} GROUP BY pillar",
            params,
        ).fetchall()
    scores = {p: 0.0 for p in PILLARS}
    for r in rows:
        if r["pillar"] in scores and r["avg_q"] is not None:
            scores[r["pillar"]] = round((float(r["avg_q"]) - 1) / 4 * 100, 1)
    return scores


def dq_score(pillar_scores: dict[str, float]) -> float:
    return round(sum(pillar_scores[p] * w for p, w in PILLAR_WEIGHTS.items()), 1)


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
            SELECT COUNT(*) AS n, AVG(quality_score) AS avg_q,
                   AVG(CASE WHEN evidence_backed THEN 1.0 ELSE 0.0 END) AS evidence_rate
            FROM interactions WHERE {where}
            """,
            params,
        ).fetchone()
    return {
        "total_interactions": int(r["n"] or 0),
        "avg_quality": round(float(r["avg_q"] or 0), 2),
        "evidence_rate": round(float(r["evidence_rate"] or 0) * 100, 1),
    }


def individual_view(org_id: str, user_id: str, name: str | None = None) -> dict:
    where, params = "org_id = %s AND user_id = %s", (org_id, user_id)
    pillars = _pillar_scores(where, params)
    phases = _phase_counts(where, params)
    with get_conn() as conn:
        usage = conn.execute(
            "SELECT usage_type, COUNT(*) AS n FROM interactions WHERE org_id=%s AND user_id=%s GROUP BY usage_type",
            (org_id, user_id),
        ).fetchall()
    return {
        "name": name,
        "pillar_scores": pillars,
        "dq_score": dq_score(pillars),
        "phase_counts": phases,
        "skipped_phases": [ph for ph, n in phases.items() if n == 0],
        "usage_breakdown": {r["usage_type"]: int(r["n"]) for r in usage},
        **_totals(where, params),
        **_baseline(org_id),
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


def team_view(org_id: str, team_id: str, *, include_members: bool) -> dict:
    with get_conn() as conn:
        members = conn.execute(
            "SELECT id, name FROM users WHERE org_id = %s AND team_id = %s ORDER BY name",
            (org_id, team_id),
        ).fetchall()
        team = conn.execute("SELECT name FROM teams WHERE id = %s", (team_id,)).fetchone()
    member_ids = [str(m["id"]) for m in members]
    where = "org_id = %s AND user_id = ANY(%s)"
    params = (org_id, member_ids)
    team_pillars = _pillar_scores(where, params) if member_ids else {p: 0.0 for p in PILLARS}
    phases = _phase_counts(where, params) if member_ids else {ph: 0 for ph in DT_PHASES}

    totals = _totals(where, params) if member_ids else {
        "total_interactions": 0,
        "avg_quality": 0,
        "evidence_rate": 0,
    }
    result = {
        "team_name": team["name"] if team else "Team",
        "team_dq": dq_score(team_pillars),
        "team_pillar_scores": team_pillars,
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
