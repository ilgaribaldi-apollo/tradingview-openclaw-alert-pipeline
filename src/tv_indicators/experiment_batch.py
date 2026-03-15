from __future__ import annotations

from typing import Any

from .config import load_test_matrix
from .experiment_backtest import run_experiment_backtest
from .experiments import list_experiments
from .reporting import append_failed_run


def run_experiment_batch(
    *,
    statuses: set[str] | None = None,
    config_name: str = "default-matrix.yaml",
    exchange: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    matrix = load_test_matrix(config_name)
    chosen_exchange = exchange or matrix.default_exchange
    for spec in list_experiments(statuses=statuses):
        for symbol in matrix.symbols:
            for timeframe in matrix.timeframes:
                try:
                    results.append(
                        run_experiment_backtest(
                            experiment_slug=spec.experiment_slug,
                            config_name=config_name,
                            exchange=chosen_exchange,
                            symbol=symbol,
                            timeframe=timeframe,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    error = f"{symbol} {timeframe} :: {exc}"
                    append_failed_run(spec.experiment_slug, error)
                    results.append({
                        "experiment_slug": spec.experiment_slug,
                        "exchange": chosen_exchange,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "error": str(exc),
                    })
    return results
