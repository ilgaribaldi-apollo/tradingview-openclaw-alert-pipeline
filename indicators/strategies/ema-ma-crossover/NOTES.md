# EMA & MA Crossover

## Source
TradingView public indicator by HPotter.

## Translation note
This is a close, clean baseline translation.
The original Pine logic is simple enough that the Python wrapper preserves it directly:
- `xMA = sma(close, LengthMA)`
- `xEMA = ema(xMA, LengthEMA)`
- long-state when `xEMA < xMA`
- short/exit-state when `xEMA > xMA`

## Why this is useful
This is a much cleaner baseline than the earlier pivot/KNN validation because:
- full source was captured
- signal semantics are explicit
- no heavy TradingView-only features are involved
