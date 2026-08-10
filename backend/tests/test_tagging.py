"""Tag sanitizer: invalid enums fall back, unknown/duplicate signals are dropped."""
from app.coach.tagging import _derive_pillar_and_quality, _sanitize


def test_invalid_phase_and_usage_fall_back():
    out = _sanitize({"phase": "nonsense", "usage_type": "nope", "fired_signals": []})
    assert out["phase"] == "define"
    assert out["usage_type"] == "ideation"


def test_unknown_signal_ids_dropped():
    out = _sanitize({"fired_signals": [{"id": "FAKE-1", "evidence": "x"}, {"id": "VAL-1", "evidence": "y"}]})
    assert [s["id"] for s in out["fired_signals"]] == ["VAL-1"]


def test_duplicate_signals_deduped():
    out = _sanitize({"fired_signals": [{"id": "VAL-1", "evidence": "a"}, {"id": "VAL-1", "evidence": "b"}]})
    assert len(out["fired_signals"]) == 1


def test_bare_string_signal_tolerated():
    out = _sanitize({"fired_signals": ["VAL-1"]})
    assert out["fired_signals"] == [{"id": "VAL-1", "evidence": ""}]


def test_evidence_truncated_to_240_chars():
    out = _sanitize({"fired_signals": [{"id": "VAL-1", "evidence": "z" * 500}]})
    assert len(out["fired_signals"][0]["evidence"]) == 240


def test_quality_from_polarity_ratio():
    # VAL-1 is +1, VAL-2 is -1 → ratio 0.5 → quality 3
    fired = [{"id": "VAL-1", "evidence": ""}, {"id": "VAL-2", "evidence": ""}]
    pillar, quality = _derive_pillar_and_quality(fired)
    assert pillar == "values"
    assert quality == 3


def test_no_signals_means_neutral_quality():
    pillar, quality = _derive_pillar_and_quality([])
    assert pillar is None
    assert quality == 3
