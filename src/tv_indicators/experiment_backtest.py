from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd
import vectorbt as vbt

from .config import load_test_matrix
from .experiment_components import apply_exit_packs, apply_filter_packs
from .experiments import load_experiment_module
from .market_data import fetch_ohlcv
from .reporting import make_run_id, write_run_outputs


def run_experiment_backtest(
    *,
    experiment_slug: str,
    config_name: str = "default-matrix.yaml",
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
) -> dict[str, Any]:
    matrix = load_test_matrix(config_name)
    exchange = exchange or matrix.default_exchange
    symbol = symbol or matrix.symbols[0]
    timeframe = timeframe or matrix.timeframes[0]
    df = fetch_ohlcv(
        exchange_name=exchange,
        symbol=symbol,
        timeframe=timeframe,
        since=matrix.date_range.get("start"),
        until=matrix.date_range.get("end"),
        limit=300,
    )
    spec, module = load_experiment_module(experiment_slug)
    if not hasattr(module, "generate_signals"):
        raise RuntimeError(f"Experiment {experiment_slug} must expose generate_signals(df)")
    signals = module.generate_signals(df.copy())
    entries = signals["entry"].fillna(False).astype(bool)
    exits = signals["exit"].fillna(False).astype(bool)
    entries = apply_filter_packs(df, entries, spec.filters)
    exits = apply_exit_packs(df, exits, spec.exits)
    fees = matrix.fees_bps / 10_000
    slippage = matrix.slippage_bps / 10_000
    portfolio = vbt.Portfolio.from_signals(
        close=df["close"],
        entries=entries,
        exits=exits,
        fees=fees,
        slippage=slippage,
        freq=timeframe,
        init_cash=1.0,
    )
    stats = portfolio.stats()
    trades = portfolio.trades.records_readable
    actual_start = df.index.min().isoformat() if len(df.index) else None
    actual_end = df.index.max().isoformat() if len(df.index) else None
    max_drawdown = _safe_float(stats.get("Max Drawdown [%]"))
    metrics = {
        "indicator_slug": spec.indicators[0] if spec.indicators else experiment_slug,
        "experiment_slug": experiment_slug,
        "experiment_family": spec.family,
        "experiment_variant": spec.variant,
        "experiment_kind": spec.kind,
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "engine": "vectorbt",
        "configured_start": matrix.date_range.get("start"),
        "configured_end": matrix.date_range.get("end"),
        "actual_start": actual_start,
        "actual_end": actual_end,
        "bar_count": int(len(df)),
        **_coverage_status(matrix.date_range.get("end"), actual_end),
        "fees_bps": matrix.fees_bps,
        "slippage_bps": matrix.slippage_bps,
        "position_sizing": matrix.position_sizing,
        "entry_signal_count": int(entries.sum()),
        "exit_signal_count": int(exits.sum()),
        "total_return": _safe_float(stats.get("Total Return [%]")),
        "max_drawdown": abs(max_drawdown) if max_drawdown is not None else None,
        "sharpe_ratio": _safe_float(stats.get("Sharpe Ratio")),
        "win_rate": _safe_float(stats.get("Win Rate [%]")),
        "trade_count": int(stats.get("Total Trades", 0) or 0),
        "filters": spec.filters,
        "exits": spec.exits,
        "notes": spec.notes or "experiment_variant",
    }
    run_id = make_run_id(experiment_slug)
    summary = _build_summary(experiment_slug, symbol, timeframe, metrics)
    output_paths = write_run_outputs(
        run_id=run_id,
        indicator_slug=spec.indicators[0] if spec.indicators else experiment_slug,
        config={
            "matrix": asdict(matrix),
            "exchange": exchange,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator_slug": spec.indicators[0] if spec.indicators else experiment_slug,
            "experiment": asdict(spec),
        },
        metrics={**metrics, "equity_final": _safe_float(portfolio.value().iloc[-1]) if len(portfolio.value()) else None},
        trades=trades,
        summary=summary,
    )
    return {"run_id": run_id, "metrics": metrics, **{k: str(v) for k, v in output_paths.items()}}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(numeric) or np.isinf(numeric):
        return None
    return numeric


def _coverage_status(configured_end: str | None, actual_end: str | None) -> dict[str, Any]:
    if not configured_end or not actual_end:
        return {"coverage_status": "unknown", "coverage_complete": False, "coverage_gap_days": None}
    configured_end_ts = pd.Timestamp(configured_end, tz="UTC")
    actual_end_ts = pd.Timestamp(actual_end)
    gap_days = max(0, int((configured_end_ts - actual_end_ts).total_seconds() // 86400))
    complete = actual_end_ts >= configured_end_ts
    return {
        "coverage_status": "complete" if complete else "incomplete",
        "coverage_complete": complete,
        "coverage_gap_days": 0 if complete else gap_days,
    }


def _build_summary(experiment_slug: str, symbol: str, timeframe: str, metrics: dict[str, Any]) -> str:
    return "\n".join([
        f"# Experiment Summary — {experiment_slug}",
        "",
        f"- Family: {metrics.get('experiment_family')}",
        f"- Variant: {metrics.get('experiment_variant')}",
        f"- Symbol: {symbol}",
        f"- Timeframe: {timeframe}",
        f"- Filters: {metrics.get('filters')}",
        f"- Exits: {metrics.get('exits')}",
        f"- Total Return [%]: {metrics.get('total_return')}",
        f"- Max Drawdown [%]: {metrics.get('max_drawdown')}",
        f"- Sharpe Ratio: {metrics.get('sharpe_ratio')}",
        f"- Win Rate [%]: {metrics.get('win_rate')}",
        f"- Trade Count: {metrics.get('trade_count')}",
    ])
