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


def _cache_path(exchange: str, symbol: str, timeframe: str, since: str | None = None, until: str | None = None) -> Path:
    safe_symbol = symbol.replace("/", "-").replace(":", "-")
    since_part = since or "start-any"
    until_part = until or "end-any"
    return ensure_dir(MARKET_DATA_DIR / exchange.lower()) / f"{safe_symbol}_{timeframe}_{since_part}_{until_part}.csv"


def fetch_ohlcv(
    *,
    exchange_name: str,
    symbol: str,
    timeframe: str,
    since: str | None = None,
    until: str | None = None,
    limit: int = 1000,
    use_cache: bool = True,
) -> pd.DataFrame:
    cache_path = _cache_path(exchange_name, symbol, timeframe, since=since, until=until)
    if use_cache and cache_path.exists():
        df = pd.read_csv(cache_path, parse_dates=["timestamp"], index_col="timestamp")
        df.index = pd.to_datetime(df.index, utc=True)
        return df

    exchange_cls = getattr(ccxt, exchange_name, None)
    if exchange_cls is None:
        raise MarketDataError(f"Unsupported exchange: {exchange_name}")
    exchange = exchange_cls({"enableRateLimit": True})
    since_ms = int(pd.Timestamp(since, tz="UTC").timestamp() * 1000) if since else None
    until_ts = pd.Timestamp(until, tz="UTC") if until else None
    timeframe_ms = TIMEFRAME_TO_MS.get(timeframe)
    if timeframe_ms is None:
        raise MarketDataError(f"Unsupported timeframe for pagination: {timeframe}")

    all_rows: list[list[float | int]] = []
    cursor = since_ms
    max_pages = 100
    for _ in range(max_pages):
        rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=limit)
        if not rows:
            break
        if all_rows:
            last_seen = all_rows[-1][0]
            rows = [row for row in rows if row[0] > last_seen]
            if not rows:
                break
        all_rows.extend(rows)
        last_ts = rows[-1][0]
        if until_ts is not None and last_ts >= int(until_ts.timestamp() * 1000):
            break
        cursor = last_ts + timeframe_ms

    if not all_rows:
        raise MarketDataError(f"No OHLCV returned for {exchange_name} {symbol} {timeframe}")
    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    if until_ts is not None:
        df = df[df.index <= until_ts]
    ensure_dir(cache_path.parent)
    df.to_csv(cache_path)
    return df
