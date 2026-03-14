from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..io import read_yaml
from ..paths import PROJECT_ROOT
from .models import RuntimeStrategyConfig

_ALLOWED_PROMOTION_VERDICTS = {
    "reject",
    "keep_researching",
    "paper_trade_candidate",
    "paper_trading",
    "live_candidate",
    "live_shadow",
    "live_enabled",
}

_PROMOTION_VERDICT_TO_STAGE = {
    "reject": "benchmarked",
    "keep_researching": "cross_validated",
    "paper_trade_candidate": "paper_trade_candidate",
    "paper_trading": "paper_trading",
    "live_candidate": "live_candidate",
    "live_shadow": "live_shadow",
    "live_enabled": "live_enabled",
}

_RUNTIME_ENABLED_VERDICTS = {
    "paper_trade_candidate",
    "paper_trading",
    "live_candidate",
    "live_shadow",
    "live_enabled",
}

_PAPER_ENABLED_VERDICTS = {
    "paper_trading",
    "live_candidate",
    "live_shadow",
    "live_enabled",
}


class StrategyPromotionError(RuntimeError):
    pass


@dataclass(slots=True)
class StrategyPromotionPayload:
    slug: str
    title: str
    source_indicator_slug: str
    owner: str | None
    version: str
    code_path: str
    config_path: str
    config_hash: str
    source_commit: str | None
    backtest_evidence: dict[str, Any]
    promotion_requirements: dict[str, Any]
    registry_metadata: dict[str, Any]
    verdict: str
    stage_to: str
    rationale: str
    reason_codes: list[str]
    strengths: list[str]
    weaknesses: list[str]
    kill_criteria: list[str]
    actor: str
    runtime_enabled: bool
    paper_enabled: bool


@dataclass(slots=True)
class PromotedStrategyBinding:
    slug: str
    title: str | None
    version: str
    code_path: str
    config_path: str
    config_hash: str | None
    stage: str
    runtime_enabled: bool
    paper_enabled: bool
    latest_verdict: str | None = None
    latest_rationale: str | None = None
    decided_at: Any = None
    backtest_evidence: dict[str, Any] | None = None
    promotion_requirements: dict[str, Any] | None = None


@dataclass(slots=True)
class PromotedStrategySummary:
    slug: str
    title: str | None
    version: str
    stage: str
    runtime_enabled: bool
    paper_enabled: bool
    latest_verdict: str | None
    latest_rationale: str | None
    decided_at: Any
    pair: str | None
    timeframe: str | None
    total_return: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    trade_count: int | None
    coverage_status: str | None


def build_strategy_promotion_payload(
    *,
    slug: str,
    run_id: str,
    version: str,
    verdict: str,
    rationale: str,
    actor: str,
    owner: str | None = None,
    project_root: Path | None = None,
) -> StrategyPromotionPayload:
    normalized_slug = slug.strip()
    normalized_version = version.strip()
    normalized_verdict = verdict.strip()
    normalized_rationale = rationale.strip()
    normalized_actor = actor.strip()
    if not normalized_slug:
        raise StrategyPromotionError("Promotion slug must not be empty")
    if not normalized_version:
        raise StrategyPromotionError("Promotion version must not be empty")
    if normalized_verdict not in _ALLOWED_PROMOTION_VERDICTS:
        raise StrategyPromotionError(
            f"Unsupported promotion verdict: {normalized_verdict}"
        )
    if not normalized_rationale:
        raise StrategyPromotionError("Promotion rationale must not be empty")
    if not normalized_actor:
        raise StrategyPromotionError("Promotion actor must not be empty")

    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    metadata_path = root / "indicators" / "metadata" / f"{normalized_slug}.yaml"
    strategy_code_path = root / "indicators" / "strategies" / normalized_slug / "logic.py"
    strategy_runtime_config_path = root / "indicators" / "strategies" / normalized_slug / "runtime.yaml"
    run_dir = root / "results" / "runs" / run_id
    run_config_path = run_dir / "config.yaml"
    run_metrics_path = run_dir / "metrics.json"
    summary_path = run_dir / "summary.md"

    if not metadata_path.exists():
        raise StrategyPromotionError(
            f"Metadata not found for {normalized_slug}: {metadata_path}"
        )
    if not strategy_code_path.exists():
        raise StrategyPromotionError(
            f"Strategy logic file not found for {normalized_slug}: {strategy_code_path}"
        )
    if not strategy_runtime_config_path.exists():
        raise StrategyPromotionError(
            "Promoted runtime config is required. "
            f"Expected {strategy_runtime_config_path}"
        )
    if not run_config_path.exists() or not run_metrics_path.exists():
        raise StrategyPromotionError(
            f"Run artifacts not found for {run_id}: {run_dir}"
        )

    metadata = read_yaml(metadata_path)
    run_config = read_yaml(run_config_path)
    metrics = json.loads(run_metrics_path.read_text(encoding="utf-8"))
    runtime_config = read_yaml(strategy_runtime_config_path)
    summary_text = summary_path.read_text(encoding="utf-8").strip() if summary_path.exists() else ""

    run_slug = str(run_config.get("indicator_slug") or metrics.get("indicator_slug") or "").strip()
    if run_slug != normalized_slug:
        raise StrategyPromotionError(
            f"Run {run_id} belongs to {run_slug or 'unknown'}, not {normalized_slug}"
        )

    candidate = _load_candidate_assessment(root=root, slug=normalized_slug)
    code_path = strategy_code_path.relative_to(root).as_posix()
    config_path = strategy_runtime_config_path.relative_to(root).as_posix()
    config_hash = hashlib.sha256(
        strategy_runtime_config_path.read_bytes()
    ).hexdigest()

    return StrategyPromotionPayload(
        slug=normalized_slug,
        title=str(metadata.get("title") or normalized_slug),
        source_indicator_slug=str(metadata.get("slug") or normalized_slug),
        owner=owner.strip() if owner and owner.strip() else None,
        version=normalized_version,
        code_path=code_path,
        config_path=config_path,
        config_hash=config_hash,
        source_commit=_resolve_source_commit(root),
        backtest_evidence=_build_backtest_evidence(
            run_id=run_id,
            run_config=run_config,
            metrics=metrics,
            summary_text=summary_text,
        ),
        promotion_requirements=_build_promotion_requirements(
            runtime_config=runtime_config,
            candidate=candidate,
        ),
        registry_metadata=_build_registry_metadata(
            slug=normalized_slug,
            metadata=metadata,
            run_id=run_id,
            runtime_config=runtime_config,
            candidate=candidate,
        ),
        verdict=normalized_verdict,
        stage_to=_PROMOTION_VERDICT_TO_STAGE[normalized_verdict],
        rationale=normalized_rationale,
        reason_codes=list(candidate.get("reasonCodes") or []),
        strengths=list(candidate.get("strengths") or []),
        weaknesses=list(candidate.get("weaknesses") or []),
        kill_criteria=list(candidate.get("killCriteria") or []),
        actor=normalized_actor,
        runtime_enabled=normalized_verdict in _RUNTIME_ENABLED_VERDICTS,
        paper_enabled=normalized_verdict in _PAPER_ENABLED_VERDICTS,
    )


def load_promoted_runtime_strategies(
    rows: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    project_root: Path | None = None,
) -> list[RuntimeStrategyConfig]:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    strategies: list[RuntimeStrategyConfig] = []
    for row in rows:
        binding = _binding_from_row(row)
        config_file = _resolve_project_path(root, binding.config_path)
        code_file = _resolve_project_path(root, binding.code_path)
        if not config_file.exists():
            raise StrategyPromotionError(
                f"Promoted runtime config file is missing for {binding.slug}@{binding.version}: {config_file}"
            )
        if not code_file.exists():
            raise StrategyPromotionError(
                f"Promoted strategy code file is missing for {binding.slug}@{binding.version}: {code_file}"
            )
        actual_hash = hashlib.sha256(config_file.read_bytes()).hexdigest()
        if binding.config_hash and binding.config_hash != actual_hash:
            raise StrategyPromotionError(
                "Promoted runtime config hash mismatch for "
                f"{binding.slug}@{binding.version}: expected {binding.config_hash}, got {actual_hash}"
            )
        config = read_yaml(config_file)
        strategies.append(
            RuntimeStrategyConfig(
                slug=binding.slug,
                version=binding.version,
                enabled=bool(config.get("enabled", True)),
                minimum_candles=int(config.get("minimum_candles", 200)),
                watchlist_keys=[str(value) for value in config.get("watchlist_keys", [])],
                signal_columns={
                    str(key): str(value)
                    for key, value in (config.get("signal_columns") or {}).items()
                },
            )
        )
    return strategies


def summarize_promoted_bindings(
    rows: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[PromotedStrategySummary]:
    items: list[PromotedStrategySummary] = []
    for row in rows:
        binding = _binding_from_row(row)
        evidence = binding.backtest_evidence or {}
        items.append(
            PromotedStrategySummary(
                slug=binding.slug,
                title=binding.title,
                version=binding.version,
                stage=binding.stage,
                runtime_enabled=binding.runtime_enabled,
                paper_enabled=binding.paper_enabled,
                latest_verdict=binding.latest_verdict,
                latest_rationale=binding.latest_rationale,
                decided_at=binding.decided_at,
                pair=_optional_text(evidence.get("symbol")),
                timeframe=_optional_text(evidence.get("timeframe")),
                total_return=_optional_float(evidence.get("total_return")),
                max_drawdown=_optional_float(evidence.get("max_drawdown")),
                sharpe_ratio=_optional_float(evidence.get("sharpe_ratio")),
                trade_count=_optional_int(evidence.get("trade_count")),
                coverage_status=_optional_text(evidence.get("coverage_status")),
            )
        )
    return items


def _binding_from_row(row: dict[str, Any]) -> PromotedStrategyBinding:
    return PromotedStrategyBinding(
        slug=str(row.get("slug") or "").strip(),
        title=_optional_text(row.get("title")),
        version=str(row.get("version") or "").strip(),
        code_path=str(row.get("code_path") or "").strip(),
        config_path=str(row.get("config_path") or "").strip(),
        config_hash=_optional_text(row.get("config_hash")),
        stage=str(row.get("current_stage") or row.get("stage") or "").strip(),
        runtime_enabled=bool(row.get("runtime_enabled", False)),
        paper_enabled=bool(row.get("paper_enabled", False)),
        latest_verdict=_optional_text(row.get("latest_verdict")),
        latest_rationale=_optional_text(row.get("latest_rationale")),
        decided_at=row.get("decided_at"),
        backtest_evidence=dict(row.get("backtest_evidence") or {}),
        promotion_requirements=dict(row.get("promotion_requirements") or {}),
    )


def _load_candidate_assessment(*, root: Path, slug: str) -> dict[str, Any]:
    candidates_path = root / "frontend" / "src" / "generated" / "candidates-index.json"
    if not candidates_path.exists():
        return {}
    payload = json.loads(candidates_path.read_text(encoding="utf-8"))
    items = payload.get("items") or []
    for item in items:
        if item.get("indicatorSlug") == slug:
            return dict(item)
    return {}


def _build_backtest_evidence(
    *,
    run_id: str,
    run_config: dict[str, Any],
    metrics: dict[str, Any],
    summary_text: str,
) -> dict[str, Any]:
    matrix = run_config.get("matrix") or {}
    date_range = matrix.get("date_range") or {}
    return {
        "run_id": run_id,
        "exchange": metrics.get("exchange") or run_config.get("exchange"),
        "symbol": metrics.get("symbol") or run_config.get("symbol"),
        "timeframe": metrics.get("timeframe") or run_config.get("timeframe"),
        "engine": metrics.get("engine"),
        "configured_start": metrics.get("configured_start") or date_range.get("start"),
        "configured_end": metrics.get("configured_end") or date_range.get("end"),
        "actual_start": metrics.get("actual_start"),
        "actual_end": metrics.get("actual_end"),
        "bar_count": metrics.get("bar_count"),
        "coverage_status": metrics.get("coverage_status"),
        "coverage_complete": metrics.get("coverage_complete"),
        "coverage_gap_days": metrics.get("coverage_gap_days"),
        "fees_bps": metrics.get("fees_bps") or matrix.get("fees_bps"),
        "slippage_bps": metrics.get("slippage_bps") or matrix.get("slippage_bps"),
        "entry_signal_count": metrics.get("entry_signal_count"),
        "exit_signal_count": metrics.get("exit_signal_count"),
        "total_return": metrics.get("total_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "win_rate": metrics.get("win_rate"),
        "trade_count": metrics.get("trade_count"),
        "notes": metrics.get("notes"),
        "summary_excerpt": summary_text[:2000] if summary_text else None,
    }


def _build_promotion_requirements(
    *,
    runtime_config: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "runtime": {
            "minimum_candles": int(runtime_config.get("minimum_candles", 200)),
            "watchlist_keys": [str(value) for value in runtime_config.get("watchlist_keys", [])],
            "signal_columns": {
                str(key): str(value)
                for key, value in (runtime_config.get("signal_columns") or {}).items()
            },
        },
        "candidateAssessment": {
            "overallScore": candidate.get("overallScore"),
            "confidenceScore": candidate.get("confidenceScore"),
            "robustnessScore": candidate.get("robustnessScore"),
            "liveReadinessScore": candidate.get("liveReadinessScore"),
            "verdict": candidate.get("verdict"),
            "recommendedNextStep": candidate.get("recommendedNextStep"),
            "runCount": candidate.get("runCount"),
            "pairs": candidate.get("pairs") or [],
            "timeframes": candidate.get("timeframes") or [],
        },
    }


def _build_registry_metadata(
    *,
    slug: str,
    metadata: dict[str, Any],
    run_id: str,
    runtime_config: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "classification": metadata.get("classification"),
        "status": metadata.get("status"),
        "repaint_risk": metadata.get("repaint_risk"),
        "latest_promoted_run_id": run_id,
        "runtime_config_path": f"indicators/strategies/{slug}/runtime.yaml",
        "watchlist_keys": [str(value) for value in runtime_config.get("watchlist_keys", [])],
        "candidate_verdict": candidate.get("verdict"),
        "candidate_overall_score": candidate.get("overallScore"),
    }


def _resolve_source_commit(project_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    commit = result.stdout.strip()
    return commit or None


def _resolve_project_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
