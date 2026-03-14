from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..io import read_yaml
from ..paths import RUNTIME_CONFIGS_DIR
from .models import (
    MarketDataCadenceConfig,
    MarketDataWorkerConfig,
    OpsHeartbeatConfig,
    OpsWorkerConfig,
    PaperWorkerConfig,
    ResearchAlignmentConfig,
    RuntimeConfig,
    RuntimeDatabaseConfig,
    RuntimeModeConfig,
    RuntimeSourceOfTruth,
    RuntimeStrategyConfig,
    RuntimeWorkersConfig,
    SignalBatchingConfig,
    SignalCadenceConfig,
    SignalWorkerConfig,
    WatchlistConfig,
)

_DEFAULT_SIGNAL_COLUMNS = {
    "entry_long": "entry",
    "exit_long": "exit",
    "entry_short": "entry_short",
    "exit_short": "exit_short",
    "flat": "flat",
}


def load_runtime_config(path: str | Path = "runtime.example.yaml") -> RuntimeConfig:
    actual_path = Path(path)
    if not actual_path.is_absolute():
        actual_path = RUNTIME_CONFIGS_DIR / actual_path
    data = read_yaml(actual_path)

    database = RuntimeDatabaseConfig(**(data.get("database") or {}))
    runtime_data = data.get("runtime") or {}
    runtime = RuntimeModeConfig(
        paper_trading_enabled=_env_bool(
            "PAPER_TRADING_ENABLED",
            runtime_data.get("paper_trading_enabled", True),
        ),
        live_execution_enabled=_env_bool(
            "LIVE_EXECUTION_ENABLED",
            runtime_data.get("live_execution_enabled", False),
        ),
        strategy_selection=str(runtime_data.get("strategy_selection", "promoted_registry")),
        source_of_truth=RuntimeSourceOfTruth(
            **(runtime_data.get("source_of_truth") or {})
        ),
    )
    watchlist = WatchlistConfig(**(data.get("watchlist") or {}))
    workers_data = data.get("workers") or {}

    market_data = _load_market_data_worker(workers_data.get("market_data") or {})
    signals = _load_signal_worker(workers_data.get("signals") or {})
    paper = _load_paper_worker(workers_data.get("paper") or {})
    ops = _load_ops_worker(workers_data.get("ops") or {})
    strategies = _load_strategies(data.get("strategies") or [])

    return RuntimeConfig(
        environment=str(os.getenv("RUNTIME_ENV", data.get("environment", "development"))),
        database=database,
        runtime=runtime,
        watchlist=watchlist,
        workers=RuntimeWorkersConfig(
            market_data=market_data,
            signals=signals,
            paper=paper,
            ops=ops,
        ),
        strategies=strategies,
        research_alignment=ResearchAlignmentConfig(**(data.get("research_alignment") or {})),
    )


def _load_market_data_worker(data: dict[str, Any]) -> MarketDataWorkerConfig:
    cadence = data.get("cadence") or {}
    return MarketDataWorkerConfig(
        enabled=bool(data.get("enabled", True)),
        worker_name=str(data.get("worker_name", "market_data")),
        fetch_limit=int(data.get("fetch_limit", 250)),
        cadence=MarketDataCadenceConfig(
            poll_seconds=int(cadence.get("poll_seconds", data.get("poll_seconds", 60))),
            align_to_candle_close=bool(cadence.get("align_to_candle_close", True)),
            write_on_new_candle_only=bool(cadence.get("write_on_new_candle_only", True)),
            lag_tolerance_seconds=int(cadence.get("lag_tolerance_seconds", 15)),
        ),
    )


def _load_signal_worker(data: dict[str, Any]) -> SignalWorkerConfig:
    cadence = data.get("cadence") or {}
    batching = data.get("batching") or {}
    return SignalWorkerConfig(
        enabled=bool(data.get("enabled", True)),
        worker_name=str(data.get("worker_name", "signals")),
        primary_source=str(data.get("primary_source", "local_evaluator")),
        optional_adapters=[str(item) for item in data.get("optional_adapters", [])],
        candle_limit=int(data.get("candle_limit", 250)),
        cadence=SignalCadenceConfig(
            poll_seconds=int(cadence.get("poll_seconds", data.get("poll_seconds", 60))),
            align_to_candle_close=bool(cadence.get("align_to_candle_close", True)),
            evaluate_on_new_candle_only=bool(cadence.get("evaluate_on_new_candle_only", True)),
            lag_tolerance_seconds=int(cadence.get("lag_tolerance_seconds", 15)),
        ),
        batching=SignalBatchingConfig(
            emit_on_state_change_only=bool(batching.get("emit_on_state_change_only", True)),
            dedupe_window_seconds=int(batching.get("dedupe_window_seconds", 21_600)),
            flush_interval_seconds=int(batching.get("flush_interval_seconds", 30)),
            max_batch_size=int(batching.get("max_batch_size", 25)),
        ),
    )


def _load_paper_worker(data: dict[str, Any]) -> PaperWorkerConfig:
    return PaperWorkerConfig(
        enabled=bool(data.get("enabled", True)),
        worker_name=str(data.get("worker_name", "paper")),
        starting_equity=float(data.get("starting_equity", 100_000)),
        max_open_positions=int(data.get("max_open_positions", 5)),
        flush_interval_seconds=int(data.get("flush_interval_seconds", 60)),
    )


def _load_ops_worker(data: dict[str, Any]) -> OpsWorkerConfig:
    heartbeat = data.get("heartbeat") or {}
    return OpsWorkerConfig(
        enabled=bool(data.get("enabled", True)),
        worker_name=str(data.get("worker_name", "ops")),
        heartbeat=OpsHeartbeatConfig(
            collect_seconds=int(
                heartbeat.get("collect_seconds", data.get("heartbeat_seconds", 30))
            ),
            flush_interval_seconds=int(heartbeat.get("flush_interval_seconds", 120)),
            max_batch_size=int(heartbeat.get("max_batch_size", 20)),
            include_stats=bool(heartbeat.get("include_stats", True)),
        ),
    )


def _load_strategies(items: list[dict[str, Any]]) -> list[RuntimeStrategyConfig]:
    strategies: list[RuntimeStrategyConfig] = []
    for item in items:
        strategies.append(
            RuntimeStrategyConfig(
                slug=str(item.get("slug", "")).strip(),
                version=str(item.get("version", "")).strip(),
                enabled=bool(item.get("enabled", True)),
                minimum_candles=int(item.get("minimum_candles", 200)),
                watchlist_keys=[str(value) for value in item.get("watchlist_keys", [])],
                signal_columns={
                    str(key): str(value)
                    for key, value in (item.get("signal_columns") or {}).items()
                }
                or dict(_DEFAULT_SIGNAL_COLUMNS),
            )
        )
    return strategies


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return bool(default)
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Environment variable {name} must be a boolean-like value")
