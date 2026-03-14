from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import ensure_dir, sanitize_json_value, write_json, write_yaml
from .paths import RANKINGS_DIR, RUNS_DIR


LEADERBOARD_COLUMNS = [
    "run_id",
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
    "coverage_status",
    "coverage_complete",
    "coverage_gap_days",
    "fees_bps",
    "slippage_bps",
    "entry_signal_count",
    "exit_signal_count",
    "total_return",
    "max_drawdown",
    "sharpe_ratio",
    "win_rate",
    "trade_count",
    "notes",
]


def make_run_id(indicator_slug: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{indicator_slug}"


def init_run_dir(run_id: str) -> Path:
    return ensure_dir(RUNS_DIR / run_id)


def write_run_outputs(
    *,
    run_id: str,
    indicator_slug: str,
    config: dict[str, Any],
    metrics: dict[str, Any],
    trades,
    summary: str,
) -> dict[str, Path]:
    run_dir = init_run_dir(run_id)
    config_path = run_dir / "config.yaml"
    metrics_path = run_dir / "metrics.json"
    trades_path = run_dir / "trades.csv"
    summary_path = run_dir / "summary.md"
    write_yaml(config_path, config)
    write_json(metrics_path, metrics)
    trades.to_csv(trades_path, index=False)
    summary_path.write_text(summary, encoding="utf-8")
    _append_leaderboard(indicator_slug, run_id, metrics)
    return {
        "run_dir": run_dir,
        "config_path": config_path,
        "metrics_path": metrics_path,
        "trades_path": trades_path,
        "summary_path": summary_path,
    }


def _append_leaderboard(indicator_slug: str, run_id: str, metrics: dict[str, Any]) -> None:
    ensure_dir(RANKINGS_DIR)
    path = RANKINGS_DIR / "leaderboard.csv"
    row = _sanitize_csv_row(
        {
            "run_id": run_id,
            "indicator_slug": indicator_slug,
            "exchange": metrics.get("exchange", ""),
            "symbol": metrics.get("symbol", ""),
            "timeframe": metrics.get("timeframe", ""),
            "engine": metrics.get("engine", metrics.get("notes", "")),
            "configured_start": metrics.get("configured_start", ""),
            "configured_end": metrics.get("configured_end", ""),
            "actual_start": metrics.get("actual_start", ""),
            "actual_end": metrics.get("actual_end", ""),
            "bar_count": metrics.get("bar_count", ""),
            "coverage_status": metrics.get("coverage_status", ""),
            "coverage_complete": metrics.get("coverage_complete", ""),
            "coverage_gap_days": metrics.get("coverage_gap_days", ""),
            "fees_bps": metrics.get("fees_bps", ""),
            "slippage_bps": metrics.get("slippage_bps", ""),
            "entry_signal_count": metrics.get("entry_signal_count", ""),
            "exit_signal_count": metrics.get("exit_signal_count", ""),
            "total_return": metrics.get("total_return", ""),
            "max_drawdown": metrics.get("max_drawdown", ""),
            "sharpe_ratio": metrics.get("sharpe_ratio", ""),
            "win_rate": metrics.get("win_rate", ""),
            "trade_count": metrics.get("trade_count", ""),
            "notes": metrics.get("notes", ""),
        }
    )
    existing_rows: list[dict[str, Any]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            existing_rows = list(reader)
    existing_rows = [r for r in existing_rows if r.get("run_id") != run_id]
    existing_rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEADERBOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(existing_rows)


def append_failed_run(indicator_slug: str, error: str) -> Path:
    ensure_dir(RANKINGS_DIR)
    path = RANKINGS_DIR / "failed_runs.csv"
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if not exists:
            writer.writerow(["indicator_slug", "error"])
        writer.writerow([indicator_slug, error])
    return path


def _sanitize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_json_value(row)
    return {key: "" if value is None else value for key, value in sanitized.items()}
