"""Dashboard metrics — pure arithmetic over the `interactions` table.

This never calls the model. It reads the rows passive tagging produced and adds them
up. The DQ score is each pillar's score (0-100) weighted and summed.
"""
from __future__ import annotations

from ..config import DT_PHASES, PILLAR_WEIGHTS
from ..db import get_conn

PILLARS = list(PILLAR_WEIGHTS.keys())


def _pillar_scores(where: str, params: tuple) -> dict[str, float]:
    """Average quality_score per pillar, mapped from the 1-5 scale to 0-100.
    Pillars with no interactions yet return 0."""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT pillar, AVG(quality_score) AS avg_q, COUNT(*) AS n
            FROM interactions
            WHERE {where}
            GROUP BY pillar
            """,
            params,
        ).fetchall()
    scores = {p: 0.0 for p in PILLARS}
    for r in rows:
        if r["pillar"] in scores and r["avg_q"] is not None:
            # 1-5 → 0-100 (linear: 1→0, 5→100)
            scores[r["pillar"]] = round((float(r["avg_q"]) - 1) / 4 * 100, 1)
    return scores


def dq_score(pillar_scores: dict[str, float]) -> float:
    return round(sum(pillar_scores[p] * w for p, w in PILLAR_WEIGHTS.items()), 1)


def _phase_counts(where: str, params: tuple) -> dict[str, int]:
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT phase, COUNT(*) AS n FROM interactions WHERE {where} GROUP BY phase",
            params,
        ).fetchall()
    counts = {ph: 0 for ph in DT_PHASES}
    for r in rows:
        if r["phase"] in counts:
            counts[r["phase"]] = int(r["n"])
    return counts


# --------------------------------------------------------------------------- #
# Employee view
# --------------------------------------------------------------------------- #
def employee_view(user_id: str) -> dict:
    pillars = _pillar_scores("user_id = %s", (user_id,))
    phases = _phase_counts("user_id = %s", (user_id,))
    with get_conn() as conn:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS n,
                   AVG(quality_score) AS avg_q,
                   AVG(CASE WHEN evidence_backed THEN 1.0 ELSE 0.0 END) AS evidence_rate
            FROM interactions WHERE user_id = %s
            """,
            (user_id,),
        ).fetchone()
        usage = conn.execute(
            "SELECT usage_type, COUNT(*) AS n FROM interactions WHERE user_id = %s GROUP BY usage_type",
            (user_id,),
        ).fetchall()
    return {
        "pillar_scores": pillars,
        "dq_score": dq_score(pillars),
        "phase_counts": phases,
        "skipped_phases": [ph for ph, n in phases.items() if n == 0],
        "usage_breakdown": {r["usage_type"]: int(r["n"]) for r in usage},
        "total_interactions": int(totals["n"] or 0),
        "avg_quality": round(float(totals["avg_q"] or 0), 2),
        "evidence_rate": round(float(totals["evidence_rate"] or 0) * 100, 1),
    }


# --------------------------------------------------------------------------- #
# Manager view — team rollup + heatmap + stagnation flags
# --------------------------------------------------------------------------- #
def manager_view(dept: str) -> dict:
    with get_conn() as conn:
        members = conn.execute("SELECT id, name FROM users WHERE dept = %s", (dept,)).fetchall()
        member_ids = [str(m["id"]) for m in members]
        # Per-pillar heatmap rows: one row per team member.
        heatmap = []
        for m in members:
            ps = _pillar_scores("user_id = %s", (str(m["id"]),))
            heatmap.append({"name": m["name"], "pillar_scores": ps, "dq": dq_score(ps)})
        # Team-wide phase counts.
        phases = _phase_counts("user_id = ANY(%s)", (member_ids,)) if member_ids else {ph: 0 for ph in DT_PHASES}
        # Stagnation: members with no interaction in the last 42 days (6 weeks).
        stagnant = []
        if member_ids:
            stag_rows = conn.execute(
                """
                SELECT u.name, MAX(i.created_at) AS last_seen
                FROM users u LEFT JOIN interactions i ON i.user_id = u.id
                WHERE u.dept = %s
                GROUP BY u.name
                HAVING MAX(i.created_at) IS NULL
                    OR MAX(i.created_at) < now() - interval '42 days'
                """,
                (dept,),
            ).fetchall()
            stagnant = [r["name"] for r in stag_rows]
    team_pillars = _pillar_scores("user_id = ANY(%s)", (member_ids,)) if member_ids else {p: 0.0 for p in PILLARS}
    return {
        "dept": dept,
        "team_dq": dq_score(team_pillars),
        "team_pillar_scores": team_pillars,
        "heatmap": heatmap,
        "phase_counts": phases,
        "most_skipped_phase": min(phases, key=phases.get) if phases else None,
        "stagnation_flags": stagnant,
    }


# --------------------------------------------------------------------------- #
# Leadership view — org DQ + trajectory vs baseline + benchmark
# --------------------------------------------------------------------------- #
def leadership_view() -> dict:
    org_pillars = _pillar_scores("TRUE", ())
    current_dq = dq_score(org_pillars)

    with get_conn() as conn:
        base_rows = conn.execute(
            "SELECT pillar, score FROM baseline WHERE scope = 'org'"
        ).fetchall()
        # Monthly DQ trajectory from interaction timestamps.
        traj_rows = conn.execute(
            """
            SELECT to_char(date_trunc('month', created_at), 'YYYY-MM') AS month,
                   AVG(quality_score) AS avg_q
            FROM interactions
            GROUP BY 1 ORDER BY 1
            """
        ).fetchall()
    baseline_pillars = {r["pillar"]: float(r["score"]) for r in base_rows}
    baseline_dq = dq_score({**{p: 0.0 for p in PILLARS}, **baseline_pillars}) if baseline_pillars else None
    trajectory = [
        {"month": r["month"], "dq": round((float(r["avg_q"]) - 1) / 4 * 100, 1)}
        for r in traj_rows
        if r["avg_q"] is not None
    ]
    # A simple illustrative industry benchmark for the demo.
    benchmark = 62.0
    return {
        "dq_score": current_dq,
        "baseline_dq": baseline_dq,
        "delta_vs_baseline": round(current_dq - baseline_dq, 1) if baseline_dq is not None else None,
        "benchmark": benchmark,
        "pillar_scores": org_pillars,
        "baseline_pillar_scores": baseline_pillars,
        "trajectory": trajectory,
    }
