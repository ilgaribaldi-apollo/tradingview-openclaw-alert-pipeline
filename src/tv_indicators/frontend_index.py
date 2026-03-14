from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .io import read_yaml
from .paths import ANALYSIS_DIR, METADATA_DIR, RUNS_DIR

FRONTEND_GENERATED_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "generated"
RANKINGS_PATH = Path(__file__).resolve().parents[2] / "results" / "rankings" / "leaderboard.csv"
FAILED_RUNS_PATH = Path(__file__).resolve().parents[2] / "results" / "rankings" / "failed_runs.csv"


def export_frontend_indexes() -> dict[str, str]:
    FRONTEND_GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    runs = _load_runs()
    indicators = _load_indicators(runs)
    rankings = _load_rankings()
    coverage = _build_coverage(indicators, runs)
    dashboard = _build_dashboard(indicators, runs, rankings)

    paths = {
        "dashboard": _write_json("dashboard-summary.json", dashboard),
        "indicators": _write_json("indicators-index.json", {"items": indicators}),
        "coverage": _write_json("coverage-matrix.json", coverage),
        "rankings": _write_json("rankings-index.json", rankings),
        "runs": _write_json("runs-index.json", {"items": runs}),
    }
    return {key: str(value) for key, value in paths.items()}


def _write_json(name: str, data: Any) -> Path:
    path = FRONTEND_GENERATED_DIR / name
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _load_indicators(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(METADATA_DIR.glob("*.yaml")):
        metadata = read_yaml(path)
        slug = path.stem
        analysis_path = ANALYSIS_DIR / slug / "analysis.yaml"
        analysis = read_yaml(analysis_path) if analysis_path.exists() else {}
        indicator_runs = [run for run in _load_runs() if run.get("indicatorSlug") == slug]
        pairs = sorted({run.get("pair", "") for run in indicator_runs if run.get("pair")})
        timeframes = sorted({run.get("timeframe", "") for run in indicator_runs if run.get("timeframe")})
        items.append(
            {
                "slug": slug,
                "title": metadata.get("title", slug),
                "author": metadata.get("author", "Unknown"),
                "classification": metadata.get("classification", "unknown"),
                "status": metadata.get("status", "raw_only"),
                "repaintRisk": metadata.get("repaint_risk", "unknown"),
                "discoveredFrom": metadata.get("discovered_from", ""),
                "pineVersion": metadata.get("pine_version", ""),
                "scriptType": metadata.get("script_type", "indicator"),
                "sourceUrl": metadata.get("source_url", ""),
                "tags": metadata.get("tags", []),
                "notes": metadata.get("notes", ""),
                "analysis": {
                    "summary": analysis.get("summary", ""),
                    "signalModel": analysis.get("signal_model", ""),
                    "cautionFlags": analysis.get("caution_flags", []),
                    "translationNotes": analysis.get("translation_notes", ""),
                },
                "coverage": {
                    "runCount": len(indicator_runs),
                    "pairs": pairs,
                    "timeframes": timeframes,
                },
            }
        )
    return items


def _load_runs() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not RUNS_DIR.exists():
        return items
    for run_dir in sorted(RUNS_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        config_path = run_dir / "config.yaml"
        metrics_path = run_dir / "metrics.json"
        summary_path = run_dir / "summary.md"
        if not config_path.exists() or not metrics_path.exists():
            continue
        config = read_yaml(config_path)
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        items.append(
            {
                "runId": run_dir.name,
                "indicatorSlug": config.get("indicator_slug") or metrics.get("indicator_slug"),
                "exchange": config.get("exchange", metrics.get("exchange", "")),
                "pair": config.get("symbol", metrics.get("symbol", "")),
                "timeframe": config.get("timeframe", metrics.get("timeframe", "")),
                "dateRange": (config.get("matrix") or {}).get("date_range", {}),
                "feesBps": (config.get("matrix") or {}).get("fees_bps"),
                "slippageBps": (config.get("matrix") or {}).get("slippage_bps"),
                "metrics": metrics,
                "summary": summary_path.read_text(encoding="utf-8") if summary_path.exists() else "",
            }
        )
    items.sort(key=lambda item: item.get("runId", ""), reverse=True)
    return items


def _load_rankings() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    if RANKINGS_PATH.exists():
        with RANKINGS_PATH.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                items.append(
                    {
                        "indicatorSlug": row.get("indicator_slug", ""),
                        "runId": row.get("run_id", ""),
                        "exchange": row.get("exchange", ""),
                        "pair": row.get("symbol", ""),
                        "timeframe": row.get("timeframe", ""),
                        "engine": row.get("engine", ""),
                        "totalReturn": _maybe_float(row.get("total_return")),
                        "maxDrawdown": _maybe_float(row.get("max_drawdown")),
                        "sharpeRatio": _maybe_float(row.get("sharpe_ratio")),
                        "winRate": _maybe_float(row.get("win_rate")),
                        "tradeCount": _maybe_int(row.get("trade_count")),
                        "notes": row.get("notes", ""),
                    }
                )
    if FAILED_RUNS_PATH.exists():
        with FAILED_RUNS_PATH.open("r", encoding="utf-8", newline="") as handle:
            failed = list(csv.DictReader(handle))
    items.sort(key=lambda item: (item.get("totalReturn") is None, -(item.get("totalReturn") or -10**9)))
    return {"items": items, "failed": failed}


def _build_coverage(indicators: list[dict[str, Any]], runs: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = sorted({run.get("pair", "") for run in runs if run.get("pair")})
    timeframes = sorted({run.get("timeframe", "") for run in runs if run.get("timeframe")})
    cells: list[dict[str, Any]] = []
    for indicator in indicators:
        slug = indicator["slug"]
        indicator_runs = [run for run in runs if run.get("indicatorSlug") == slug]
        for pair in pairs or [""]:
            for timeframe in timeframes or [""]:
                matching = [run for run in indicator_runs if run.get("pair") == pair and run.get("timeframe") == timeframe]
                latest = matching[0] if matching else None
                cells.append(
                    {
                        "indicatorSlug": slug,
                        "indicatorTitle": indicator["title"],
                        "pair": pair,
                        "timeframe": timeframe,
                        "status": "tested" if latest else indicator.get("status", "raw_only"),
                        "runId": latest.get("runId") if latest else None,
                        "totalReturn": latest.get("metrics", {}).get("total_return") if latest else None,
                    }
                )
    return {"pairs": pairs, "timeframes": timeframes, "cells": cells}


def _build_dashboard(
    indicators: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    rankings: dict[str, Any],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    for indicator in indicators:
        status_counts[indicator["status"]] = status_counts.get(indicator["status"], 0) + 1
        classification_counts[indicator["classification"]] = (
            classification_counts.get(indicator["classification"], 0) + 1
        )
    top_ranked = rankings.get("items", [])[:5]
    recent_runs = runs[:5]
    return {
        "totals": {
            "indicators": len(indicators),
            "runs": len(runs),
            "ranked": len(rankings.get("items", [])),
            "failedRuns": len(rankings.get("failed", [])),
        },
        "statusCounts": status_counts,
        "classificationCounts": classification_counts,
        "topRanked": top_ranked,
        "recentRuns": recent_runs,
    }


def _maybe_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _maybe_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None
