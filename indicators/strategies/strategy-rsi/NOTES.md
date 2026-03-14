# Strategy RSI

## Source
TradingView public indicator by HPotter.

## Translation note
This is a clean baseline translation of the literal Pine state logic:
- compute RSI(12)
- set state to `1` when RSI > 70
- set state to `-1` when RSI < 30
- otherwise carry forward prior state

## Important
This is not a claim that the logic is good. It is a faithful batch-validation artifact.
