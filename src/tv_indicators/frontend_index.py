from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import read_yaml, write_json
from .paths import ANALYSIS_DIR, METADATA_DIR, RUNS_DIR
from .runtime import RuntimeReadModelQueries, load_runtime_config
from .runtime.promotion import summarize_promoted_bindings
from .runtime.store import PostgresRuntimeStore, RuntimeStoreError

FRONTEND_GENERATED_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "generated"
RANKINGS_PATH = Path(__file__).resolve().parents[2] / "results" / "rankings" / "leaderboard.csv"
FAILED_RUNS_PATH = Path(__file__).resolve().parents[2] / "results" / "rankings" / "failed_runs.csv"


def export_frontend_indexes(*, runtime_config_name: str = "runtime.example.yaml") -> dict[str, str]:
    FRONTEND_GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    runs = _load_runs()
    rankings = _load_rankings()
    candidates = _build_candidates(runs, rankings)
    indicators = _load_indicators(runs, candidates)
    coverage = _build_coverage(indicators, runs)
    diagnostics = _build_diagnostics(candidates)
    live_readiness = _build_live_readiness(candidates)
    dashboard = _build_dashboard(indicators, runs, rankings, candidates)
    runtime_snapshots = _load_runtime_snapshots(runtime_config_name=runtime_config_name)

    paths = {
        "dashboard": _write_json("dashboard-summary.json", dashboard),
        "indicators": _write_json("indicators-index.json", {"items": indicators}),
        "coverage": _write_json("coverage-matrix.json", coverage),
        "rankings": _write_json("rankings-index.json", rankings),
        "runs": _write_json("runs-index.json", {"items": runs}),
        "candidates": _write_json("candidates-index.json", {"items": candidates}),
        "diagnostics": _write_json("diagnostics-index.json", diagnostics),
        "live_readiness": _write_json("live-readiness-index.json", {"items": live_readiness}),
        "runtime_signals": _write_json("runtime-signals.json", runtime_snapshots["signals"]),
        "runtime_ops": _write_json("runtime-ops.json", runtime_snapshots["ops"]),
    }
    return {key: str(value) for key, value in paths.items()}


def _write_json(name: str, data: Any) -> Path:
    path = FRONTEND_GENERATED_DIR / name
    write_json(path, data)
    return path


def _load_indicators(
    runs: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    candidate_map = {item["indicatorSlug"]: item for item in candidates}
    items: list[dict[str, Any]] = []
    for path in sorted(METADATA_DIR.glob("*.yaml")):
        metadata = read_yaml(path)
        slug = path.stem
        analysis_path = ANALYSIS_DIR / slug / "analysis.yaml"
        analysis = read_yaml(analysis_path) if analysis_path.exists() else {}
        indicator_runs = [run for run in runs if run.get("indicatorSlug") == slug]
        pairs = sorted({run.get("pair", "") for run in indicator_runs if run.get("pair")})
        timeframes = sorted({run.get("timeframe", "") for run in indicator_runs if run.get("timeframe")})
        candidate = candidate_map.get(slug, {})
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
                "assessment": candidate,
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
                "actualRange": {
                    "start": metrics.get("actual_start"),
                    "end": metrics.get("actual_end"),
                },
                "barCount": metrics.get("bar_count"),
                "coverageStatus": metrics.get("coverage_status"),
                "coverageComplete": metrics.get("coverage_complete"),
                "coverageGapDays": metrics.get("coverage_gap_days"),
                "feesBps": (config.get("matrix") or {}).get("fees_bps", metrics.get("fees_bps")),
                "slippageBps": (config.get("matrix") or {}).get("slippage_bps", metrics.get("slippage_bps")),
                "engine": metrics.get("engine", metrics.get("notes")),
                "metrics": metrics,
                "summary": summary_path.read_text(encoding="utf-8") if summary_path.exists() else "",
            }
        )
    items.sort(key=lambda item: item.get("runId", ""), reverse=True)
    return items


def _load_rankings() -> dict[str, Any]:
    history_items: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    if RANKINGS_PATH.exists():
        with RANKINGS_PATH.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                history_items.append(
                    {
                        "indicatorSlug": row.get("indicator_slug", ""),
                        "runId": row.get("run_id", ""),
                        "exchange": row.get("exchange", ""),
                        "pair": row.get("symbol", ""),
                        "timeframe": row.get("timeframe", ""),
                        "engine": row.get("engine", ""),
                        "configuredStart": row.get("configured_start", ""),
                        "configuredEnd": row.get("configured_end", ""),
                        "actualStart": row.get("actual_start", ""),
                        "actualEnd": row.get("actual_end", ""),
                        "barCount": _maybe_int(row.get("bar_count")),
                        "coverageStatus": row.get("coverage_status", ""),
                        "coverageComplete": _maybe_bool(row.get("coverage_complete")),
                        "coverageGapDays": _maybe_int(row.get("coverage_gap_days")),
                        "feesBps": _maybe_float(row.get("fees_bps")),
                        "slippageBps": _maybe_float(row.get("slippage_bps")),
                        "entrySignalCount": _maybe_int(row.get("entry_signal_count")),
                        "exitSignalCount": _maybe_int(row.get("exit_signal_count")),
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
    latest_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in history_items:
        key = (item.get("indicatorSlug", ""), item.get("pair", ""), item.get("timeframe", ""))
        current = latest_map.get(key)
        if current is None or item.get("runId", "") > current.get("runId", ""):
            latest_map[key] = item
    items = list(latest_map.values())
    items.sort(key=lambda item: (item.get("totalReturn") is None, -(_finite_number(item.get("totalReturn")) or -10**9)))
    history_items.sort(key=lambda item: item.get("runId", ""), reverse=True)
    return {"items": items, "history": history_items, "failed": failed}


def _build_candidates(runs: list[dict[str, Any]], rankings: dict[str, Any]) -> list[dict[str, Any]]:
    runs_by_indicator: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        runs_by_indicator.setdefault(run["indicatorSlug"], []).append(run)

    ranking_map: dict[str, list[dict[str, Any]]] = {}
    for row in rankings.get("items", []):
        ranking_map.setdefault(row["indicatorSlug"], []).append(row)

    failed_by_indicator = Counter()
    for row in rankings.get("failed", []):
        failed_by_indicator[row.get("indicator_slug", "")] += 1

    assessments = []
    for slug, indicator_runs in runs_by_indicator.items():
        ranking_rows = ranking_map.get(slug, [])
        returns = [row["totalReturn"] for row in ranking_rows if row.get("totalReturn") is not None]
        drawdowns = [abs(row["maxDrawdown"]) for row in ranking_rows if row.get("maxDrawdown") is not None]
        sharpes = [row["sharpeRatio"] for row in ranking_rows if row.get("sharpeRatio") is not None]
        trade_counts = [row["tradeCount"] for row in ranking_rows if row.get("tradeCount") is not None]
        pairs = sorted({run.get("pair") for run in indicator_runs if run.get("pair")})
        timeframes = sorted({run.get("timeframe") for run in indicator_runs if run.get("timeframe")})
        avg_return = _avg(returns)
        avg_sharpe = _avg(sharpes)
        avg_drawdown = _avg(drawdowns)
        avg_trades = _avg(trade_counts)

        return_score = _clamp((avg_return or 0) * 8, 0, 30)
        sharpe_score = _clamp((avg_sharpe or 0) * 4, 0, 20)
        drawdown_score = _clamp(20 - (avg_drawdown or 0) * 4, 0, 20)
        trade_score = _clamp((avg_trades or 0) * 2, 0, 10)
        breadth_score = _clamp(len(pairs) * 8 + len(timeframes) * 5, 0, 20)
        failed_penalty = min(failed_by_indicator.get(slug, 0) * 8, 20)

        overall_score = round(
            return_score + sharpe_score + drawdown_score + trade_score + breadth_score - failed_penalty,
            2,
        )
        robustness_score = round(_clamp(drawdown_score + breadth_score + trade_score - failed_penalty / 2, 0, 100), 2)
        confidence_score = round(_clamp((len(indicator_runs) * 15) + trade_score + breadth_score - failed_penalty, 0, 100), 2)

        live_readiness_score = round(
            _clamp(robustness_score * 0.45 + confidence_score * 0.35 + _clamp(sharpe_score * 2, 0, 40) * 0.2, 0, 100),
            2,
        )

        strengths = []
        weaknesses = []
        reason_codes = []
        failure_modes = []
        kill_criteria = []

        if (avg_return or 0) > 4:
            strengths.append("Positive average return across recorded runs")
            reason_codes.append("positive_return_profile")
        else:
            weaknesses.append("Return profile is still weak or too narrow")
            reason_codes.append("weak_return_profile")

        if (avg_sharpe or 0) >= 2:
            strengths.append("Risk-adjusted returns look healthy")
            reason_codes.append("healthy_risk_adjusted_profile")
        else:
            weaknesses.append("Sharpe profile needs more evidence")
            failure_modes.append("Risk-adjusted performance may collapse out of sample")
            reason_codes.append("low_sharpe_confidence")

        if (avg_drawdown or 99) <= 5:
            strengths.append("Drawdown has stayed relatively contained")
            reason_codes.append("contained_drawdown")
        else:
            weaknesses.append("Drawdown is too large for easy live confidence")
            failure_modes.append("Live behavior may be psychologically hard to hold")
            kill_criteria.append("Reject if drawdown expands materially in broader matrix testing")
            reason_codes.append("drawdown_risk")

        if len(pairs) >= 2:
            strengths.append("Evidence spans more than one pair")
            reason_codes.append("cross_pair_signal")
        else:
            weaknesses.append("Too concentrated in one pair so far")
            kill_criteria.append("Do not promote without cross-pair confirmation")
            reason_codes.append("single_pair_bias")

        incomplete_coverage_runs = [run for run in indicator_runs if run.get("metrics", {}).get("coverage_complete") is False]
        if incomplete_coverage_runs:
            weaknesses.append("One or more runs have incomplete configured history coverage")
            failure_modes.append("Rankings may overstate confidence because provider history is truncated")
            kill_criteria.append("Do not trust leaderboard placement until coverage is complete or explicitly accepted")
            reason_codes.append("incomplete_history_coverage")

        if failed_by_indicator.get(slug, 0) > 0:
            weaknesses.append("Some matrix cells failed and need diagnosis")
            failure_modes.append("Implementation or market-data fragility still present")
            reason_codes.append("matrix_failures_present")

        if (avg_trades or 0) < 3:
            weaknesses.append("Trade count is light; sample may be too thin")
            kill_criteria.append("Reject if out-of-sample still yields too few trades")
            reason_codes.append("thin_sample_size")

        if live_readiness_score >= 75 and confidence_score >= 55:
            verdict = "paper_trade_candidate"
            recommended_next_step = "Run paper-trade shadow monitoring and out-of-sample validation next."
        elif overall_score >= 55:
            verdict = "keep_researching"
            recommended_next_step = "Expand pair/timeframe coverage and add fee/slippage stress tests."
        else:
            verdict = "reject"
            recommended_next_step = "Do not promote yet; either improve evidence quality or move on."

        assessments.append(
            {
                "indicatorSlug": slug,
                "overallScore": overall_score,
                "confidenceScore": confidence_score,
                "robustnessScore": robustness_score,
                "liveReadinessScore": live_readiness_score,
                "verdict": verdict,
                "reasonCodes": reason_codes,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "failureModes": failure_modes,
                "killCriteria": kill_criteria,
                "recommendedNextStep": recommended_next_step,
                "runCount": len(indicator_runs),
                "pairs": pairs,
                "timeframes": timeframes,
                "latestRunId": indicator_runs[0].get("runId") if indicator_runs else None,
            }
        )

    assessments.sort(key=lambda item: item["overallScore"], reverse=True)
    return assessments


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


def _build_diagnostics(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for item in candidates:
        items.append(
            {
                "indicatorSlug": item["indicatorSlug"],
                "verdict": item["verdict"],
                "weaknesses": item["weaknesses"],
                "failureModes": item["failureModes"],
                "killCriteria": item["killCriteria"],
                "reasonCodes": item["reasonCodes"],
            }
        )
    return {"items": items}


def _build_live_readiness(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for item in candidates:
        blockers = []
        if item["confidenceScore"] < 55:
            blockers.append("Need more evidence across additional runs")
        if item["robustnessScore"] < 55:
            blockers.append("Robustness still too weak for paper/live promotion")
        if "single_pair_bias" in item["reasonCodes"]:
            blockers.append("Cross-pair validation missing")
        if "thin_sample_size" in item["reasonCodes"]:
            blockers.append("Trade count is too thin")
        if "incomplete_history_coverage" in item["reasonCodes"]:
            blockers.append("Configured history coverage is incomplete")
        items.append(
            {
                "indicatorSlug": item["indicatorSlug"],
                "liveReadinessScore": item["liveReadinessScore"],
                "verdict": item["verdict"],
                "nextStage": "paper_trading" if item["verdict"] == "paper_trade_candidate" else "research",
                "blockers": blockers,
                "recommendedNextStep": item["recommendedNextStep"],
            }
        )
    return items


def _build_dashboard(
    indicators: list[dict[str, Any]],
    runs: list[dict[str, Any]],
    rankings: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    verdict_counts: dict[str, int] = {}
    for indicator in indicators:
        status_counts[indicator["status"]] = status_counts.get(indicator["status"], 0) + 1
        classification_counts[indicator["classification"]] = (
            classification_counts.get(indicator["classification"], 0) + 1
        )
    for candidate in candidates:
        verdict_counts[candidate["verdict"]] = verdict_counts.get(candidate["verdict"], 0) + 1
    top_ranked = rankings.get("items", [])[:5]
    recent_runs = runs[:5]
    top_candidates = candidates[:4]
    return {
        "totals": {
            "indicators": len(indicators),
            "runs": len(runs),
            "ranked": len(rankings.get("items", [])),
            "failedRuns": len(rankings.get("failed", [])),
        },
        "statusCounts": status_counts,
        "classificationCounts": classification_counts,
        "verdictCounts": verdict_counts,
        "topRanked": top_ranked,
        "topCandidates": top_candidates,
        "recentRuns": recent_runs,
    }


def _load_runtime_snapshots(*, runtime_config_name: str) -> dict[str, dict[str, Any]]:
    generated_at = datetime.now(UTC).isoformat()
    try:
        config = load_runtime_config(runtime_config_name)
        store = PostgresRuntimeStore.from_database_config(config.database)
        queries = RuntimeReadModelQueries(store)
        bindings = store.list_runtime_strategy_bindings(limit=12)
        promoted = summarize_promoted_bindings(bindings)
        return {
            "signals": {
                "status": "ok",
                "generatedAt": generated_at,
                "items": queries.recent_signals(limit=50),
                "promotedStrategies": promoted,
            },
            "ops": {
                "status": "ok",
                "generatedAt": generated_at,
                "items": queries.ops_overview(limit=20),
                "promotedStrategies": promoted,
            },
        }
    except RuntimeStoreError as exc:
        return _empty_runtime_snapshots(generated_at=generated_at, error=str(exc))
    except Exception as exc:
        return _empty_runtime_snapshots(generated_at=generated_at, error=str(exc))



def _empty_runtime_snapshots(*, generated_at: str, error: str) -> dict[str, dict[str, Any]]:
    payload = {
        "status": "unavailable",
        "generatedAt": generated_at,
        "error": error,
        "items": [],
        "promotedStrategies": [],
    }
    return {"signals": dict(payload), "ops": dict(payload)}



def _avg(values: list[float | int | None]) -> float | None:
    clean = [_finite_number(value) for value in values]
    filtered = [value for value in clean if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    finite = _finite_number(value)
    if finite is None:
        return min_value
    return max(min_value, min(finite, max_value))


def _maybe_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return _finite_number(float(value))
    except ValueError:
        return None


def _maybe_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        numeric = float(value)
    except ValueError:
        return None
    if not math.isfinite(numeric):
        return None
    return int(numeric)


def _maybe_bool(value: str | None) -> bool | None:
    if value in (None, ""):
        return None
    lowered = str(value).strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


def _finite_number(value: float | int | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return numeric
