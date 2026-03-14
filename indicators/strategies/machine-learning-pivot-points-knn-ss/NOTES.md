# Machine Learning Pivot Points (KNN) [SS]

## Important
This is the first live workflow validation using a real TradingView indicator.

## Honesty note
The TradingView source capture for this script appears partial in the current browser extraction flow.
So this Python strategy is **not** a full Pine-equivalent implementation.

It is a pragmatic approximation based on the visible logic:
- confirmed pivot highs/lows
- short-term slope direction
- long on pivot-low + positive slope
- exit on pivot-high + negative slope

## Status
Use this as a pipeline-validation artifact, not as a trusted faithful port.

## Runner
Backtests for this strategy should now use the project's Python 3.13 + `vectorbt` environment.
