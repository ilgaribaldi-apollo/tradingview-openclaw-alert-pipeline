# Runtime Workers

Workers are separated by lane so failures are easier to isolate.

## Lanes
- `market_data/` — fetch/update candles for approved watchlist rows
- `signals/` — evaluate promoted strategies against current market state
- `paper/` — simulate fills/positions from approved signal events
- `ops/` — persist heartbeats, lag, and incident summaries

All workers must be restart-safe and dedupe-safe.
