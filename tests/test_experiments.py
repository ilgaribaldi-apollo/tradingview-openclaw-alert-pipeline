from __future__ import annotations

from tv_indicators.experiments import list_experiments, load_experiment_spec


def test_load_experiment_spec_reads_seeded_variant():
    spec, base_dir = load_experiment_spec("rsi-baseline-30-70")
    assert spec.experiment_slug == "rsi-baseline-30-70"
    assert spec.family == "rsi-thresholds"
    assert spec.status == "active"
    assert base_dir.name == "rsi-baseline-30-70"


def test_list_experiments_returns_seeded_items():
    slugs = {spec.experiment_slug for spec in list_experiments(statuses={"active"})}
    assert "rsi-baseline-30-70" in slugs
    assert "signal-ma-cross-50" in slugs
    assert "rsi-macd-confirmation-v1" in slugs
