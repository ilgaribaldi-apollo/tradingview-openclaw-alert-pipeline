from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import ensure_dir, write_json, write_yaml
from .paths import RANKINGS_DIR, RUNS_DIR


LEADERBOARD_COLUMNS = [
    "run_id",
    "indicator_slug",
    "exchange",
    "symbol",
    "timeframe",
    "engine",
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
    row = {
        "run_id": run_id,
        "indicator_slug": indicator_slug,
        "exchange": metrics.get("exchange", ""),
        "symbol": metrics.get("symbol", ""),
        "timeframe": metrics.get("timeframe", ""),
        "engine": metrics.get("notes", ""),
        "total_return": metrics.get("total_return", ""),
        "max_drawdown": metrics.get("max_drawdown", ""),
        "sharpe_ratio": metrics.get("sharpe_ratio", ""),
        "win_rate": metrics.get("win_rate", ""),
        "trade_count": metrics.get("trade_count", ""),
        "notes": metrics.get("notes", ""),
    }
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
