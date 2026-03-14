# Batch Testing

## Goal
Run each strategy-ready indicator across the full benchmark matrix, not just one lucky pair.

## Current default matrix
- exchange: `coinbase`
- symbols:
  - `BTC/USD`
  - `ETH/USD`
  - `SOL/USD`
  - `DOGE/USD`
- timeframes:
  - `1h`

## Rule
Batch mode should expand the matrix as:
- each indicator
- x each symbol
- x each timeframe

That means rankings reflect broader crypto robustness rather than single-pair luck.

## CLI
```bash
source .venv/bin/activate
tvir batch --status strategy_ready --config default-matrix.yaml
```

## Outputs
- one run folder per successful matrix cell under `results/runs/`
- one leaderboard row per successful run
- one failed-runs row per failed matrix cell
- refreshed frontend generated indexes after the batch completes

## Reliability expectations
Batch mode should:
- keep going when one matrix cell fails
- record failures with pair + timeframe context
- preserve append-only run history
- make frontend observability update automatically
