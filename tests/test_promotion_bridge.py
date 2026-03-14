from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tv_indicators.io import write_json, write_yaml
from tv_indicators.runtime.promotion import (
    StrategyPromotionError,
    build_strategy_promotion_payload,
    load_promoted_runtime_strategies,
    summarize_promoted_bindings,
)


@pytest.fixture()
def seeded_project(tmp_path: Path) -> Path:
    metadata_path = tmp_path / "indicators" / "metadata" / "strategy-rsi.yaml"
    strategy_dir = tmp_path / "indicators" / "strategies" / "strategy-rsi"
    run_dir = tmp_path / "results" / "runs" / "run-1"
    generated_dir = tmp_path / "frontend" / "src" / "generated"

    write_yaml(
        metadata_path,
        {
            "slug": "strategy-rsi",
            "title": "Strategy RSI",
            "status": "benchmarked",
            "classification": "signal_capable",
            "repaint_risk": "low",
        },
    )
    strategy_dir.mkdir(parents=True, exist_ok=True)
    (strategy_dir / "logic.py").write_text("def generate_signals(df):\n    return df\n", encoding="utf-8")
    (strategy_dir / "runtime.yaml").write_text(
        "minimum_candles: 180\nwatchlist_keys:\n  - coinbase:BTC/USD:1h\nsignal_columns:\n  entry_long: entry\n  exit_long: exit\n",
        encoding="utf-8",
    )

    write_yaml(
        run_dir / "config.yaml",
        {
            "indicator_slug": "strategy-rsi",
            "exchange": "coinbase",
            "symbol": "BTC/USD",
            "timeframe": "1h",
            "matrix": {
                "date_range": {"start": "2023-01-01", "end": "2026-01-01"},
                "fees_bps": 10,
                "slippage_bps": 5,
            },
        },
    )
    write_json(
        run_dir / "metrics.json",
        {
            "indicator_slug": "strategy-rsi",
            "exchange": "coinbase",
            "symbol": "BTC/USD",
            "timeframe": "1h",
            "engine": "vectorbt",
            "configured_start": "2023-01-01",
            "configured_end": "2026-01-01",
            "actual_start": "2023-01-01T00:00:00+00:00",
            "actual_end": "2026-01-01T00:00:00+00:00",
            "bar_count": 26297,
            "coverage_status": "complete",
            "coverage_complete": True,
            "coverage_gap_days": 0,
            "fees_bps": 10,
            "slippage_bps": 5,
            "entry_signal_count": 133,
            "exit_signal_count": 132,
            "total_return": 121.02,
            "max_drawdown": 35.74,
            "sharpe_ratio": 0.94,
            "win_rate": 39.39,
            "trade_count": 133,
            "notes": "vectorbt",
        },
    )
    (run_dir / "summary.md").write_text("# Backtest Summary\n\nLooks solid enough for a conservative runtime lane.\n", encoding="utf-8")
    write_json(
        generated_dir / "candidates-index.json",
        {
            "items": [
                {
                    "indicatorSlug": "strategy-rsi",
                    "overallScore": 82.5,
                    "confidenceScore": 68.0,
                    "robustnessScore": 61.0,
                    "liveReadinessScore": 74.0,
                    "verdict": "paper_trade_candidate",
                    "reasonCodes": ["positive_return_profile", "cross_pair_signal"],
                    "strengths": ["Positive return profile"],
                    "weaknesses": ["Still needs more out-of-sample time"],
                    "failureModes": [],
                    "killCriteria": ["Reject if drawdown expands materially"],
                    "recommendedNextStep": "Promote into conservative runtime monitoring.",
                    "runCount": 4,
                    "pairs": ["BTC/USD", "ETH/USD"],
                    "timeframes": ["1h"],
                    "latestRunId": "run-1",
                }
            ]
        },
    )

    return tmp_path


def test_build_strategy_promotion_payload_collects_backtest_and_candidate_context(seeded_project: Path):
    payload = build_strategy_promotion_payload(
        slug="strategy-rsi",
        run_id="run-1",
        version="promoted-v1",
        verdict="paper_trade_candidate",
        rationale="Best recent run is good enough for a conservative shadow lane.",
        actor="apollo",
        owner="apollo",
        project_root=seeded_project,
    )

    assert payload.slug == "strategy-rsi"
    assert payload.version == "promoted-v1"
    assert payload.stage_to == "paper_trade_candidate"
    assert payload.runtime_enabled is True
    assert payload.paper_enabled is False
    assert payload.backtest_evidence["run_id"] == "run-1"
    assert payload.backtest_evidence["total_return"] == 121.02
    assert payload.promotion_requirements["runtime"]["minimum_candles"] == 180
    assert payload.promotion_requirements["candidateAssessment"]["verdict"] == "paper_trade_candidate"
    assert payload.reason_codes == ["positive_return_profile", "cross_pair_signal"]
    assert payload.config_hash == hashlib.sha256(
        (seeded_project / "indicators" / "strategies" / "strategy-rsi" / "runtime.yaml").read_bytes()
    ).hexdigest()


def test_load_promoted_runtime_strategies_requires_pinned_hash_and_builds_runtime_configs(seeded_project: Path):
    runtime_config_path = seeded_project / "indicators" / "strategies" / "strategy-rsi" / "runtime.yaml"
    config_hash = hashlib.sha256(runtime_config_path.read_bytes()).hexdigest()
    rows = [
        {
            "slug": "strategy-rsi",
            "title": "Strategy RSI",
            "current_stage": "paper_trade_candidate",
            "runtime_enabled": True,
            "paper_enabled": False,
            "version": "promoted-v1",
            "code_path": "indicators/strategies/strategy-rsi/logic.py",
            "config_path": "indicators/strategies/strategy-rsi/runtime.yaml",
            "config_hash": config_hash,
            "latest_verdict": "paper_trade_candidate",
            "latest_rationale": "Looks good",
            "backtest_evidence": {"symbol": "BTC/USD", "timeframe": "1h", "trade_count": 133},
            "promotion_requirements": {"runtime": {"minimum_candles": 180}},
        }
    ]

    strategies = load_promoted_runtime_strategies(rows, project_root=seeded_project)
    summary = summarize_promoted_bindings(rows)

    assert len(strategies) == 1
    assert strategies[0].identity_key == "strategy-rsi@promoted-v1"
    assert strategies[0].minimum_candles == 180
    assert strategies[0].watchlist_keys == ["coinbase:BTC/USD:1h"]
    assert strategies[0].signal_columns["entry_long"] == "entry"
    assert summary[0].slug == "strategy-rsi"
    assert summary[0].trade_count == 133

    with pytest.raises(StrategyPromotionError, match="hash mismatch"):
        load_promoted_runtime_strategies(
            [{**rows[0], "config_hash": "not-the-real-hash"}],
            project_root=seeded_project,
        )


def test_build_strategy_promotion_payload_requires_strategy_runtime_config(seeded_project: Path):
    runtime_config_path = seeded_project / "indicators" / "strategies" / "strategy-rsi" / "runtime.yaml"
    runtime_config_path.unlink()

    with pytest.raises(StrategyPromotionError, match="Promoted runtime config is required"):
        build_strategy_promotion_payload(
            slug="strategy-rsi",
            run_id="run-1",
            version="promoted-v1",
            verdict="paper_trade_candidate",
            rationale="Need the bridge to be strict.",
            actor="apollo",
            project_root=seeded_project,
        )
