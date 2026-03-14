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
        limit=3000,
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
    metrics = {
        "indicator_slug": indicator_slug,
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "total_return": _safe_float(stats.get("Total Return [%]")),
        "max_drawdown": _safe_float(stats.get("Max Drawdown [%]")),
        "sharpe_ratio": _safe_float(stats.get("Sharpe Ratio")),
        "win_rate": _safe_float(stats.get("Win Rate [%]")),
        "trade_count": int(stats.get("Total Trades", 0) or 0),
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
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _build_summary(indicator_slug: str, symbol: str, timeframe: str, metrics: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Backtest Summary — {indicator_slug}",
            "",
            f"- Symbol: {symbol}",
            f"- Timeframe: {timeframe}",
            f"- Total Return [%]: {metrics.get('total_return')}",
            f"- Max Drawdown [%]: {metrics.get('max_drawdown')}",
            f"- Sharpe Ratio: {metrics.get('sharpe_ratio')}",
            f"- Win Rate [%]: {metrics.get('win_rate')}",
            f"- Trade Count: {metrics.get('trade_count')}",
            f"- Notes: {metrics.get('notes')}",
        ]
    )
