from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd
import vectorbt as vbt

from .config import load_test_matrix
from .market_data import fetch_ohlcv
from .reporting import make_run_id, write_run_outputs
from .strategy_loader import load_strategy_module


def run_indicator_backtest(
    *,
    indicator_slug: str,
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
    strategy_module = load_strategy_module(indicator_slug)
    if not hasattr(strategy_module, "generate_signals"):
        raise RuntimeError(f"Strategy {indicator_slug} must expose generate_signals(df)")
    signals = strategy_module.generate_signals(df.copy())
    entries = signals["entry"].fillna(False).astype(bool)
    exits = signals["exit"].fillna(False).astype(bool)
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
    total_return = _safe_float(stats.get("Total Return [%]"))
    max_drawdown = _safe_float(stats.get("Max Drawdown [%]"))
    sharpe_ratio = _safe_float(stats.get("Sharpe Ratio"))
    win_rate = _normalize_metric(_safe_float(stats.get("Win Rate [%]")))
    trade_count = int(stats.get("Total Trades", 0) or 0)
    coverage = _coverage_status(
        configured_start=matrix.date_range.get("start"),
        configured_end=matrix.date_range.get("end"),
        actual_start=actual_start,
        actual_end=actual_end,
    )
    metrics = {
        "indicator_slug": indicator_slug,
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "engine": "vectorbt",
        "configured_start": matrix.date_range.get("start"),
        "configured_end": matrix.date_range.get("end"),
        "actual_start": actual_start,
        "actual_end": actual_end,
        "bar_count": int(len(df)),
        **coverage,
        "fees_bps": matrix.fees_bps,
        "slippage_bps": matrix.slippage_bps,
        "position_sizing": matrix.position_sizing,
        "entry_signal_count": int(entries.sum()),
        "exit_signal_count": int(exits.sum()),
        "total_return": total_return,
        "max_drawdown": abs(max_drawdown) if max_drawdown is not None else None,
        "sharpe_ratio": sharpe_ratio,
        "win_rate": win_rate,
        "trade_count": trade_count,
        "notes": "vectorbt",
    }
    run_id = make_run_id(indicator_slug)
    summary = _build_summary(indicator_slug, symbol, timeframe, metrics)
    output_paths = write_run_outputs(
        run_id=run_id,
        indicator_slug=indicator_slug,
        config={
            "matrix": asdict(matrix),
            "exchange": exchange,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicator_slug": indicator_slug,
        },
        metrics={**metrics, "equity_final": _safe_float(portfolio.value().iloc[-1]) if len(portfolio.value()) else None},
        trades=trades,
        summary=summary,
    )
    return {"run_id": run_id, "metrics": metrics, **{k: str(v) for k, v in output_paths.items()}}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int, np.floating, np.integer)):
        value = float(value)
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    if isinstance(value, str):
        try:
            parsed = float(value)
            if np.isnan(parsed) or np.isinf(parsed):
                return None
            return parsed
        except ValueError:
            return None
    return None


def _normalize_metric(value: float | None) -> float | None:
    if value is None:
        return None
    if np.isnan(value) or np.isinf(value):
        return None
    return float(value)


def _coverage_status(
    *,
    configured_start: str | None,
    configured_end: str | None,
    actual_start: str | None,
    actual_end: str | None,
) -> dict[str, Any]:
    if not configured_end or not actual_end:
        return {
            "coverage_status": "unknown",
            "coverage_complete": False,
            "coverage_gap_days": None,
        }
    configured_end_ts = pd.Timestamp(configured_end, tz="UTC")
    actual_end_ts = pd.Timestamp(actual_end)
    gap_days = max(0, int((configured_end_ts - actual_end_ts).total_seconds() // 86400))
    coverage_complete = actual_end_ts >= configured_end_ts
    return {
        "coverage_status": "complete" if coverage_complete else "incomplete",
        "coverage_complete": coverage_complete,
        "coverage_gap_days": 0 if coverage_complete else gap_days,
    }


def _build_summary(indicator_slug: str, symbol: str, timeframe: str, metrics: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Backtest Summary — {indicator_slug}",
            "",
            f"- Exchange: {metrics.get('exchange')}",
            f"- Symbol: {symbol}",
            f"- Timeframe: {timeframe}",
            f"- Configured Range: {metrics.get('configured_start')} -> {metrics.get('configured_end')}",
            f"- Actual Range: {metrics.get('actual_start')} -> {metrics.get('actual_end')}",
            f"- Bar Count: {metrics.get('bar_count')}",
            f"- Coverage Status: {metrics.get('coverage_status')}",
            f"- Coverage Complete: {metrics.get('coverage_complete')}",
            f"- Coverage Gap [days]: {metrics.get('coverage_gap_days')}",
            f"- Fees [bps]: {metrics.get('fees_bps')}",
            f"- Slippage [bps]: {metrics.get('slippage_bps')}",
            f"- Entry Signal Count: {metrics.get('entry_signal_count')}",
            f"- Exit Signal Count: {metrics.get('exit_signal_count')}",
            f"- Total Return [%]: {metrics.get('total_return')}",
            f"- Max Drawdown [%]: {metrics.get('max_drawdown')}",
            f"- Sharpe Ratio: {metrics.get('sharpe_ratio')}",
            f"- Win Rate [%]: {metrics.get('win_rate')}",
            f"- Trade Count: {metrics.get('trade_count')}",
            f"- Engine: {metrics.get('engine')}",
            f"- Notes: {metrics.get('notes')}",
        ]
    )
