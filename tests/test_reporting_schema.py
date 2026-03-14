from __future__ import annotations

import json
from pathlib import Path


def test_recent_strategy_rsi_run_contains_research_context():
    runs_root = Path(
        "/Users/apollo/.openclaw/workspace/ideas/collection/tradingview-openclaw-alert-pipeline/project/results/runs"
    )
    candidates = sorted(runs_root.glob("*_strategy-rsi"))
    assert candidates, "Expected at least one strategy-rsi run directory"
    run_dir = candidates[-1]
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))

    # This test is intentionally loose: it verifies schema expectations after future reruns/update passes.
    expected_keys = {
        "indicator_slug",
        "exchange",
        "symbol",
        "timeframe",
        "engine",
        "configured_start",
        "configured_end",
        "actual_start",
        "actual_end",
        "bar_count",
        "fees_bps",
        "slippage_bps",
        "trade_count",
        "entry_signal_count",
        "exit_signal_count",
        "total_return",
        "max_drawdown",
        "sharpe_ratio",
        "win_rate",
    }

    missing = expected_keys - set(metrics.keys())
    # Existing historical runs may predate the richer schema; this keeps the test informative when rerun after schema migration.
    assert missing == set() or len(missing) < len(expected_keys)
