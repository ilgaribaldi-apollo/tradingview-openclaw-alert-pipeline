# TradingView Indicator Research Pipeline

This directory is the implementation/workspace area for indicator intake, analysis, Python translation, backtesting, and comparison.

## Layout
- `indicators/raw/` — exact Pine source as extracted from TradingView
- `indicators/metadata/` — sidecar metadata files
- `indicators/analysis/` — structured interpretation before translation
- `indicators/normalized/` — minimally cleaned/standardized variants
- `indicators/strategies/` — backtestable Python wrappers/adaptations (+ pinned `runtime.yaml` files for promoted runtime versions)
- `indicators/catalog/` — aggregate catalog/index files
- `data/market/` — cached OHLCV datasets for repeatable comparisons
- `backtests/configs/` — backtest matrices and run configs (default crypto basket includes BTC/ETH/SOL/DOGE)
- `backtests/runners/` — execution scripts or runner notes
- `backtests/suites/` — smoke/benchmark suite definitions
- `results/runs/` — immutable per-run output folders
- `results/rankings/` — cross-run comparisons and failed-run logs
- `docs/` — operator workflow docs and templates
- `docs/workflow-blueprint.md` — end-to-end runbook for TradingView skill -> Python backtest -> frontend observability
- `docs/runtime-foundation.md` — Sprint 2 runtime/db scaffold notes
- `docs/neon-runtime-env.md` — Neon-ready environment and schema-apply notes
- `runtime/` — paper-trading runtime scaffold (configs, workers, adapters, state)
- `db/` — Neon/Postgres operational schema, queries, migrations, and seed examples
- `api/` — shared runtime/webhook contracts for Python + Next.js boundaries
- `src/tv_indicators/` — Python package and CLI
- `frontend/` — Next.js + shadcn observability app reading normalized generated indexes

## Rules
1. Never edit files in `indicators/raw/` after intake.
2. Every indicator gets metadata before adaptation.
3. Every serious indicator gets an analysis artifact before translation.
4. Every strategy wrapper documents its interpretation assumptions.
5. Every backtest run stores config + metrics + trades + summary.
6. Rejecting an indicator is allowed; forcing bad scripts into fake strategies is not.

## CLI
After creating the project-local UV environment and installing the project:

```bash
uv venv --python /opt/homebrew/bin/python3.13 .venv
source .venv/bin/activate
uv pip install -e .
```

Examples:

```bash
tvir ingest --metadata path/to/metadata.yaml --source path/to/source.pine --analysis path/to/analysis.yaml
tvir backtest example-ema-cross --config default-matrix.yaml --exchange coinbase --symbol BTC/USD --timeframe 1h
tvir batch --status strategy_ready --config default-matrix.yaml
tvir export-frontend

tvir runtime promote strategy-rsi \
  --config runtime.example.yaml \
  --run-id 20260314T222812Z_strategy-rsi \
  --version strategy-rsi-v1 \
  --verdict paper_trade_candidate \
  --rationale "Best current conservative candidate for runtime monitoring"

tvir runtime worker market-data --config runtime.example.yaml --once
tvir runtime worker signals --config runtime.example.yaml --once
tvir runtime worker ops --config runtime.example.yaml --once

tvir runtime read-model signals --config runtime.example.yaml --limit 20
tvir runtime read-model ops --config runtime.example.yaml --limit 20
```

Ingest, backtest, and batch commands now refresh the frontend generated indexes automatically.
JSON/CLI exports are sanitized so non-finite numeric values are written as `null` instead of invalid `NaN`/`Infinity` JSON.

## Opinionated workflow
- use TradingView for discovery and Pine extraction
- use Python for translation and testing
- keep runtime state separate from research truth
- only batch-test indicators that are actually ready
- keep results append-only so comparisons stay honest

## Runtime foundation status
- `runtime/`, `db/`, and `api/` now include the first real runtime worker foundation
- the database foundation is SQL-first and Neon-ready so Python workers and the Next.js app can share one operational schema later
- live order execution is still explicitly out of scope
- current runtime support now includes:
  - candle-aligned market-data polling
  - local strategy signal evaluation with deduped `signal_events` writes
  - batched/upserted `runtime_worker_status` heartbeats
  - read-model helper plumbing for future `/signals` and `/ops`
- runtime cadence is intentionally conservative:
  - poll market data on candle boundaries, not tiny moves
  - write signal events only on state changes / deduped triggers
  - batch heartbeats and non-critical stats on an interval before writing to Neon
  - keep frontend reads on aggregated/read-model-friendly queries where possible

## Market data source right now
- default exchange: `coinbase`
- default crypto basket: `BTC/USD`, `ETH/USD`, `SOL/USD`, `DOGE/USD`
- reason: Binance public API returned a 451 geo-restriction error from this environment, so Coinbase is the current reliable default

## Tests
Run:

```bash
source .venv/bin/activate
pytest -q
ruff check src tests
cd frontend && npm run lint && npm run typecheck && npm run build
```
