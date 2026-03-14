from __future__ import annotations

from tv_indicators import batch as batch_module


def test_run_batch_iterates_full_matrix(monkeypatch):
    monkeypatch.setattr(batch_module, "list_indicator_slugs", lambda statuses=None: ["alpha", "beta"])

    calls = []

    class DummyMatrix:
        default_exchange = "coinbase"
        symbols = ["BTC/USD", "ETH/USD"]
        timeframes = ["1h", "4h"]

    monkeypatch.setattr(batch_module, "load_test_matrix", lambda _: DummyMatrix())

    def fake_run_indicator_backtest(*, indicator_slug, config_name, exchange, symbol, timeframe):
        calls.append((indicator_slug, config_name, exchange, symbol, timeframe))
        return {
            "indicator_slug": indicator_slug,
            "exchange": exchange,
            "symbol": symbol,
            "timeframe": timeframe,
        }

    monkeypatch.setattr(batch_module, "run_indicator_backtest", fake_run_indicator_backtest)

    results = batch_module.run_batch(statuses={"strategy_ready"}, config_name="default-matrix.yaml")

    assert len(calls) == 8
    assert len(results) == 8
    assert calls[0] == ("alpha", "default-matrix.yaml", "coinbase", "BTC/USD", "1h")
    assert calls[-1] == ("beta", "default-matrix.yaml", "coinbase", "ETH/USD", "4h")


def test_run_batch_records_failed_runs_per_matrix_cell(monkeypatch):
    monkeypatch.setattr(batch_module, "list_indicator_slugs", lambda statuses=None: ["alpha"])

    class DummyMatrix:
        default_exchange = "coinbase"
        symbols = ["BTC/USD", "ETH/USD"]
        timeframes = ["1h"]

    monkeypatch.setattr(batch_module, "load_test_matrix", lambda _: DummyMatrix())

    failures = []

    def fake_run_indicator_backtest(*, indicator_slug, config_name, exchange, symbol, timeframe):
        if symbol == "ETH/USD":
            raise RuntimeError("boom")
        return {"indicator_slug": indicator_slug, "symbol": symbol, "timeframe": timeframe}

    def fake_append_failed_run(indicator_slug, error):
        failures.append((indicator_slug, error))

    monkeypatch.setattr(batch_module, "run_indicator_backtest", fake_run_indicator_backtest)
    monkeypatch.setattr(batch_module, "append_failed_run", fake_append_failed_run)

    results = batch_module.run_batch(config_name="default-matrix.yaml")

    assert len(results) == 2
    assert results[0]["symbol"] == "BTC/USD"
    assert results[1]["indicator_slug"] == "alpha"
    assert results[1]["symbol"] == "ETH/USD"
    assert "error" in results[1]
    assert failures == [("alpha", "ETH/USD 1h :: boom")]
