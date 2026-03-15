from __future__ import annotations

from tv_indicators import experiment_batch as experiment_batch_module


def test_run_experiment_batch_iterates_matrix(monkeypatch):
    class DummySpec:
        def __init__(self, slug: str):
            self.experiment_slug = slug

    monkeypatch.setattr(experiment_batch_module, "list_experiments", lambda statuses=None: [DummySpec("exp-a")])

    class DummyMatrix:
        default_exchange = "coinbase"
        symbols = ["BTC/USD", "ETH/USD"]
        timeframes = ["1h", "4h"]

    monkeypatch.setattr(experiment_batch_module, "load_test_matrix", lambda _: DummyMatrix())
    calls = []

    def fake_run_experiment_backtest(*, experiment_slug, config_name, exchange, symbol, timeframe):
        calls.append((experiment_slug, exchange, symbol, timeframe))
        return {"experiment_slug": experiment_slug, "symbol": symbol, "timeframe": timeframe}

    monkeypatch.setattr(experiment_batch_module, "run_experiment_backtest", fake_run_experiment_backtest)

    results = experiment_batch_module.run_experiment_batch(statuses={"active"}, config_name="default-matrix.yaml")
    assert len(results) == 4
    assert calls[0] == ("exp-a", "coinbase", "BTC/USD", "1h")
    assert calls[-1] == ("exp-a", "coinbase", "ETH/USD", "4h")
