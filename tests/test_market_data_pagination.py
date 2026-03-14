from __future__ import annotations

import pandas as pd

from tv_indicators import market_data
from tv_indicators.market_data import fetch_ohlcv


class PaginatedExchange:
    shared_calls = []

    def __init__(self, config=None):
        self.config = config or {}

    def fetch_ohlcv(self, symbol, timeframe="1h", since=None, limit=1000):
        self.__class__.shared_calls.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "since": since,
            "limit": limit,
        })
        if since is None:
            raise AssertionError("since should be set in this test")
        # two pages of 300 1h candles each
        if len(self.__class__.shared_calls) == 1:
            start = pd.Timestamp("2023-01-01T00:00:00Z")
            return [
                [int((start + pd.Timedelta(hours=i)).timestamp() * 1000), 1, 2, 0.5, 1.5, 10]
                for i in range(300)
            ]
        if len(self.__class__.shared_calls) == 2:
            start = pd.Timestamp("2023-01-13T12:00:00Z")
            return [
                [int((start + pd.Timedelta(hours=i)).timestamp() * 1000), 1, 2, 0.5, 1.5, 10]
                for i in range(300)
            ]
        return []


def test_fetch_ohlcv_paginates_until_end(tmp_path, monkeypatch):
    monkeypatch.setattr(market_data, "MARKET_DATA_DIR", tmp_path / "market")
    PaginatedExchange.shared_calls = []
    monkeypatch.setattr(market_data.ccxt, "coinbase", PaginatedExchange)

    df = fetch_ohlcv(
        exchange_name="coinbase",
        symbol="BTC/USD",
        timeframe="1h",
        since="2023-01-01",
        until="2023-01-20",
        limit=300,
        use_cache=False,
    )

    assert len(PaginatedExchange.shared_calls) >= 2
    assert len(df) == 457
    assert df.index.min().isoformat() == "2023-01-01T00:00:00+00:00"
    assert df.index.max().isoformat() == "2023-01-20T00:00:00+00:00"
