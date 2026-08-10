"""Scoring math: pillar scores from signal counts, weighted DQ blend."""
from app.coach.signals import PILLARS
from app.dashboard.metrics import MIN_EVIDENCE, _pillar_scores, dq_score


def _counts(**overrides):
    base = {p: {"pos": 0, "neg": 0} for p in PILLARS}
    base.update(overrides)
    return base


def test_pillar_below_min_evidence_is_none():
    scores = _pillar_scores(_counts(values={"pos": MIN_EVIDENCE - 1, "neg": 0}))
    assert scores["values"] is None


def test_pillar_all_positive_is_100():
    scores = _pillar_scores(_counts(values={"pos": MIN_EVIDENCE, "neg": 0}))
    assert scores["values"] == 100.0


def test_pillar_mixed_ratio():
    scores = _pillar_scores(_counts(process={"pos": 3, "neg": 1}))
    assert scores["process"] == 75.0


def test_dq_none_when_no_pillar_has_data():
    assert dq_score({p: None for p in PILLARS}) is None


def test_dq_single_pillar_equals_that_pillar():
    scores = {p: None for p in PILLARS}
    scores["values"] = 80.0
    assert dq_score(scores) == 80.0


def test_dq_weights_renormalise_over_active_pillars():
    scores = {p: None for p in PILLARS}
    scores["values"] = 100.0   # weight 0.25
    scores["process"] = 0.0    # weight 0.10
    # (100*0.25 + 0*0.10) / 0.35 = 71.4
    assert dq_score(scores) == 71.4
