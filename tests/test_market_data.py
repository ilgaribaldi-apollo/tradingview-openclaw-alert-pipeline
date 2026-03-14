from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tv_indicators import market_data
from tv_indicators.market_data import MarketDataError, fetch_ohlcv


class DummyExchange:
    shared_calls = []

    def __init__(self, config=None):
        self.config = config or {}

    def fetch_ohlcv(self, symbol, timeframe="1h", since=None, limit=1000):
        self.__class__.shared_calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "since": since,
                "limit": limit,
            }
        )
        return [
            [1704067200000, 100.0, 110.0, 95.0, 105.0, 1000.0],
            [1704070800000, 105.0, 112.0, 101.0, 108.0, 900.0],
        ]


class EmptyExchange(DummyExchange):
    def fetch_ohlcv(self, symbol, timeframe="1h", since=None, limit=1000):
        return []


def test_fetch_ohlcv_returns_normalized_dataframe(tmp_path, monkeypatch):
    monkeypatch.setattr(market_data, "MARKET_DATA_DIR", tmp_path / "market")
    monkeypatch.setattr(market_data.ccxt, "coinbase", DummyExchange)

    df = fetch_ohlcv(
        exchange_name="coinbase",
        symbol="BTC/USD",
        timeframe="1h",
        since="2024-01-01",
        limit=2,
        use_cache=False,
    )

    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert str(df.index.tz) == "UTC"
    assert df.index.is_monotonic_increasing
    assert df.iloc[0]["close"] == 105.0


def test_fetch_ohlcv_writes_and_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(market_data, "MARKET_DATA_DIR", tmp_path / "market")
    monkeypatch.setattr(market_data.ccxt, "coinbase", DummyExchange)

    first = fetch_ohlcv(
        exchange_name="coinbase",
        symbol="ETH/USD",
        timeframe="1h",
        use_cache=True,
        limit=2,
    )
    cache_file = tmp_path / "market" / "coinbase" / "ETH-USD_1h_start-any_end-any.csv"
    assert cache_file.exists()

    class FailingExchange(DummyExchange):
        def fetch_ohlcv(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("cache should have been used")

    monkeypatch.setattr(market_data.ccxt, "coinbase", FailingExchange)
    second = fetch_ohlcv(
        exchange_name="coinbase",
        symbol="ETH/USD",
        timeframe="1h",
        use_cache=True,
        limit=2,
    )

    assert list(first.index) == list(second.index)
    pd.testing.assert_frame_equal(
        first.reset_index(drop=True),
        second.reset_index(drop=True),
        check_freq=False,
        check_dtype=False,
    )


def test_fetch_ohlcv_raises_for_unsupported_exchange(tmp_path, monkeypatch):
    monkeypatch.setattr(market_data, "MARKET_DATA_DIR", tmp_path / "market")

    with pytest.raises(MarketDataError, match="Unsupported exchange"):
        fetch_ohlcv(
            exchange_name="definitely_not_real",
            symbol="BTC/USD",
            timeframe="1h",
            use_cache=False,
        )


def test_fetch_ohlcv_raises_for_empty_result(tmp_path, monkeypatch):
    monkeypatch.setattr(market_data, "MARKET_DATA_DIR", tmp_path / "market")
    monkeypatch.setattr(market_data.ccxt, "coinbase", EmptyExchange)

    with pytest.raises(MarketDataError, match="No OHLCV returned"):
        fetch_ohlcv(
            exchange_name="coinbase",
            symbol="BTC/USD",
            timeframe="1h",
            use_cache=False,
        )
