# Comparison Workflow

## Goal
Make many-indicator comparison boring, consistent, and defensible.

## Rules
1. Use the same cached dataset when comparing multiple indicators.
2. Use the same fee/slippage assumptions.
3. Keep one default benchmark matrix and version it when changed.
4. Separate failed runs from valid runs; do not hide errors.
5. Keep caveat notes near rankings.

## Suggested comparison dimensions
- exchange
- symbol
- timeframe
- engine
- total return
- max drawdown
- Sharpe ratio
- win rate
- trade count
- robustness notes

## Ranking schema
Leaderboard rows should record:
- `run_id`
- `indicator_slug`
- `exchange`
- `symbol`
- `timeframe`
- `engine`
- `configured_start`
- `configured_end`
- `actual_start`
- `actual_end`
- `bar_count`
- `fees_bps`
- `slippage_bps`
- `entry_signal_count`
- `exit_signal_count`
- `total_return`
- `max_drawdown`
- `sharpe_ratio`
- `win_rate`
- `trade_count`
- `notes`

## Practical loop
- ingest indicators
- analyze and classify them
- translate only promising ones
- mark them `strategy_ready`
- run batch tests on that status group across the full benchmark matrix
- inspect leaderboard + frontend observability views + individual run summaries
