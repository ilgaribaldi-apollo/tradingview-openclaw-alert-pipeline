from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from ..market_data import fetch_ohlcv
from ..strategy_loader import load_strategy_module
from .models import RuntimeStrategyConfig, SignalEventCandidate, WatchlistEntry
from .services import timeframe_to_seconds

_SIGNAL_STATE_BY_TYPE = {
    "entry_long": "long",
    "exit_long": "flat",
    "entry_short": "short",
    "exit_short": "flat",
    "flat": "flat",
}


class RuntimeAdapterError(RuntimeError):
    pass


class CCXTClosedCandlePoller:
    def __init__(self, *, now_provider: Callable[[], datetime] | None = None) -> None:
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def fetch_closed_candles(
        self,
        *,
        watchlist: WatchlistEntry,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        timeframe_seconds = timeframe_to_seconds(watchlist.timeframe)
        try:
            frame = fetch_ohlcv(
                exchange_name=watchlist.venue,
                symbol=watchlist.symbol,
                timeframe=watchlist.timeframe,
                limit=limit or 250,
                use_cache=False,
            )
        except Exception as exc:  # pragma: no cover - network/runtime integration surface
            raise RuntimeAdapterError(
                f"Unable to fetch market data for {watchlist.key}: {exc}"
            ) from exc

        now = _as_utc(self._now_provider())
        closed_before = now - timedelta(seconds=timeframe_seconds)
        closed = frame[frame.index <= closed_before]
        if closed.empty:
            return []

        candles: list[dict[str, Any]] = []
        for timestamp, row in closed.tail(limit or 250).iterrows():
            candle_open_at = _as_utc(timestamp.to_pydatetime())
            candle_close_at = candle_open_at + timedelta(seconds=timeframe_seconds)
            candles.append(
                {
                    "open_time": candle_open_at,
                    "candle_open_at": candle_open_at,
                    "candle_close_at": candle_close_at,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
        return candles


class LocalStrategySignalEvaluator:
    def __init__(
        self,
        *,
        strategies: Sequence[RuntimeStrategyConfig],
        module_loader: Callable[[str], Any] | None = None,
    ) -> None:
        self._strategies = [strategy for strategy in strategies if strategy.enabled]
        self._module_loader = module_loader or load_strategy_module
        self._module_cache: dict[str, Any] = {}

    def evaluate(
        self,
        *,
        watchlist: WatchlistEntry,
        candles: Sequence[dict[str, Any]],
    ) -> list[SignalEventCandidate]:
        if not candles or not self._strategies:
            return []
        frame = _candles_to_frame(candles)
        results: list[SignalEventCandidate] = []
        timeframe_seconds = timeframe_to_seconds(watchlist.timeframe)

        for strategy in self._strategies:
            if not strategy.applies_to(watchlist.key):
                continue
            if len(frame) < strategy.minimum_candles:
                continue
            module = self._load_module(strategy.slug)
            generate_signals = getattr(module, "generate_signals", None)
            if not callable(generate_signals):
                raise RuntimeAdapterError(
                    f"Strategy {strategy.slug} does not expose a callable generate_signals(df)"
                )
            try:
                signal_frame = generate_signals(frame.copy())
            except Exception as exc:
                raise RuntimeAdapterError(
                    "Strategy evaluation failed for "
                    f"{strategy.identity_key} on {watchlist.key}: {exc}"
                ) from exc
            if signal_frame.empty:
                continue
            latest = signal_frame.iloc[-1]
            candle_open_at = _resolve_row_timestamp(signal_frame, fallback=frame.index[-1])
            candle_close_at = candle_open_at + timedelta(seconds=timeframe_seconds)
            price = _optional_float(latest.get("close"))

            for signal_type, column_name in strategy.signal_columns.items():
                if not _is_truthy(latest.get(column_name)):
                    continue
                results.append(
                    SignalEventCandidate(
                        strategy_slug=strategy.slug,
                        strategy_version=strategy.version,
                        venue=watchlist.venue,
                        symbol=watchlist.symbol,
                        timeframe=watchlist.timeframe,
                        signal_type=signal_type,
                        signal_at=candle_close_at,
                        candle_open_at=candle_open_at,
                        candle_close_at=candle_close_at,
                        signal_source="local_evaluator",
                        state=_SIGNAL_STATE_BY_TYPE.get(signal_type, signal_type),
                        price=price,
                        context={
                            "strategy_identity": strategy.identity_key,
                            "signal_column": column_name,
                            "candle_open_at": candle_open_at.isoformat(),
                            "candle_close_at": candle_close_at.isoformat(),
                            "close": price,
                        },
                    )
                )
        return results

    def _load_module(self, slug: str) -> Any:
        cached = self._module_cache.get(slug)
        if cached is not None:
            return cached
        try:
            module = self._module_loader(slug)
        except Exception as exc:
            raise RuntimeAdapterError(f"Unable to load strategy module {slug}: {exc}") from exc
        self._module_cache[slug] = module
        return module


def _candles_to_frame(candles: Sequence[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(candles)
    if frame.empty:
        return frame
    timestamp_column = "candle_open_at" if "candle_open_at" in frame.columns else "open_time"
    frame[timestamp_column] = pd.to_datetime(frame[timestamp_column], utc=True)
    frame = frame.set_index(timestamp_column).sort_index()
    frame.index.name = "timestamp"
    return frame


def _resolve_row_timestamp(frame: pd.DataFrame, *, fallback: Any) -> datetime:
    index_value = frame.index[-1]
    if hasattr(index_value, "to_pydatetime"):
        return _as_utc(index_value.to_pydatetime())
    if isinstance(index_value, datetime):
        return _as_utc(index_value)
    return _as_utc(pd.Timestamp(fallback, tz="UTC").to_pydatetime())


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if hasattr(value, "item"):
        try:
            return bool(value.item())
        except Exception:  # pragma: no cover - defensive edge case
            return bool(value)
    return bool(value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
