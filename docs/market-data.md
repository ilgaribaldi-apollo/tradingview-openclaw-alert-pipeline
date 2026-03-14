# Market Data

## Current default
The project currently uses **Coinbase via CCXT** as the default crypto OHLCV source.

## Why not Binance right now?
In this environment, Binance returned a **451 geo-restriction error** on public API access. That makes it a bad default here, even though Binance would otherwise be a natural crypto data source.

## Current baseline setup
- provider layer: `ccxt`
- exchange: `coinbase`
- default symbols:
  - `BTC/USD`
  - `ETH/USD`
  - `SOL/USD`
  - `DOGE/USD`
- timeframe: `1h`

## Reliability goals
We want the market-data layer to be boring and trustworthy.

That means:
- normalize OHLCV into a consistent DataFrame shape
- keep timestamps UTC-aware
- cache fetched data locally for reproducible comparisons
- fail loudly on unsupported exchanges or empty responses
- keep exchange selection configurable via the test matrix

## Current test coverage
- normalized OHLCV DataFrame shape
- cache write + cache reuse
- unsupported exchange error
- empty OHLCV response error

## Future hardening ideas
- add freshness/age checks on cached files
- add schema validation for required columns
- add smoke test against the live default exchange
- add multi-exchange fallback order when one provider fails
- add provider-health status into the frontend observability surface
