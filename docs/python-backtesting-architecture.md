# Python Backtesting Architecture

## Stack
- `ccxt` for exchange OHLCV ingestion
- `pandas` / `numpy` for data handling
- `vectorbt` for scalable backtesting and comparison
- `PyYAML` for config-driven runs

## Note on engine choice
This project now uses a local Python 3.13 + `uv` environment so `vectorbt` is supported cleanly. Do not use the host Python 3.14 runtime for project backtests.

## Directory roles
- `indicators/raw/` — upstream Pine truth
- `indicators/metadata/` — provenance and status
- `indicators/analysis/` — structured interpretation before translation
- `indicators/normalized/` — optional cleanup or partial Pine normalization
- `indicators/strategies/` — translated Python strategy logic
- `data/market/` — cached OHLCV datasets
- `backtests/configs/` — reusable test matrices
- `results/runs/` — immutable per-run outputs
- `results/rankings/` — aggregate comparisons

## Scalability rule
Backtest outputs should be append-only per run. Never overwrite prior results just to keep things tidy. Comparison belongs in aggregate artifacts, not by mutating history.

## Recommended indicator lifecycle
1. `raw_only`
2. `analyzed`
3. `strategy_ready`
4. `benchmarked`
5. `rejected` or `promoted`

## Default crypto coverage
The default benchmark matrix should cover more than one pair so we can test whether an indicator only "works" on BTC.
Current default basket:
- `BTC/USD`
- `ETH/USD`
- `SOL/USD`
- `DOGE/USD`

## Market data source right now
- default exchange: `coinbase`
- current reason: Binance access from this environment returned a 451 geo-restriction error, so Coinbase is the active default until we intentionally add another source

## Reliability checks
The data layer should be covered by tests that verify:
- OHLCV normalization into a UTC-indexed DataFrame
- cache write/read behavior
- unsupported exchange handling
- empty response handling

## Batch testing rule
Only batch indicators whose metadata status implies they are actually strategy-ready. Do not waste time running visual-only junk through the engine.
