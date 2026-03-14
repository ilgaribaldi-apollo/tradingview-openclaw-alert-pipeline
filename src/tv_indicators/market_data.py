from __future__ import annotations

from pathlib import Path

import ccxt
import pandas as pd

from .io import ensure_dir
from .paths import MARKET_DATA_DIR


TIMEFRAME_TO_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


class MarketDataError(RuntimeError):
    pass


def _cache_path(exchange: str, symbol: str, timeframe: str) -> Path:
    safe_symbol = symbol.replace("/", "-").replace(":", "-")
    return ensure_dir(MARKET_DATA_DIR / exchange.lower()) / f"{safe_symbol}_{timeframe}.csv"


def fetch_ohlcv(
    *,
    exchange_name: str,
    symbol: str,
    timeframe: str,
    since: str | None = None,
    limit: int = 1000,
    use_cache: bool = True,
) -> pd.DataFrame:
    cache_path = _cache_path(exchange_name, symbol, timeframe)
    if use_cache and cache_path.exists():
        df = pd.read_csv(cache_path, parse_dates=["timestamp"], index_col="timestamp")
        df.index = pd.to_datetime(df.index, utc=True)
        return df

    exchange_cls = getattr(ccxt, exchange_name, None)
    if exchange_cls is None:
        raise MarketDataError(f"Unsupported exchange: {exchange_name}")
    exchange = exchange_cls({"enableRateLimit": True})
    since_ms = None
    if since:
        since_ms = int(pd.Timestamp(since, tz="UTC").timestamp() * 1000)
    rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
    if not rows:
        raise MarketDataError(f"No OHLCV returned for {exchange_name} {symbol} {timeframe}")
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    ensure_dir(cache_path.parent)
    df.to_csv(cache_path)
    return df
