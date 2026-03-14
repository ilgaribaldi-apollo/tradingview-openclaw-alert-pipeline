# Market Data Cache

Local OHLCV cache for repeatable backtests.

Suggested rule:
- fetch from exchange
- cache locally
- rerun tests against the same cached dataset when comparing indicators

That prevents fake comparisons caused by changing source data between runs.
