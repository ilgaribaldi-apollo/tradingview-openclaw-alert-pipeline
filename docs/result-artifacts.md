# Result Artifacts

## Goal
Every backtest run should be auditable and comparable without guessing what assumptions produced it.

## Required run outputs
Each run folder should contain:
- `config.yaml`
- `metrics.json`
- `trades.csv`
- `summary.md`

## Required metrics context
At minimum, `metrics.json` and leaderboard exports should capture:
- indicator slug
- exchange
- symbol
- timeframe
- engine
- configured start/end
- actual realized start/end
- bar count
- fees bps
- slippage bps
- position sizing
- entry signal count
- exit signal count
- total return
- max drawdown
- sharpe ratio
- win rate
- trade count

## Why this matters
A result without realized horizon, bar count, and cost assumptions is not properly comparable.
It may still be interesting, but it is not trustworthy enough for ranking.
