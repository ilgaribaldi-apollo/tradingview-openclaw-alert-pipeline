# Runtime Foundation — Sprint 2/3 bridge

This slice moves the runtime lane from pure scaffold to a first real Python worker foundation without changing current research/backtesting behavior.

## What was added
- real Python worker runners for:
  - market-data cadence/freshness polling
  - local signal evaluation + deduped signal event flushing
  - ops/runtime heartbeat flushing
- a Neon/Postgres store adapter boundary (`PostgresRuntimeStore`) for:
  - deduped `signal_events`
  - upserted `runtime_worker_status`
  - explicit strategy promotion writes into `strategy_registry`, `strategy_versions`, and `promotion_decisions`
  - read-model-friendly `/signals` and `/ops` query helpers
- strict promotion-bound runtime selection:
  - `tvir runtime promote ...` writes the promoted/version-pinned runtime record
  - signal workers now load only runtime-enabled promoted strategy/version rows
  - promoted versions must carry a pinned `indicators/strategies/<slug>/runtime.yaml` config hash
- frontend runtime snapshots for first real `/signals` and `/ops` pages
- example runtime env + seed files for safe local Neon bootstrap
- tests covering worker loops, buffering, store behavior, promotion bridging, and read-model helpers

## What was deliberately not added
- no live execution code
- no broker credentials
- no broker/exchange write paths
- no webhook server
- no paper position executor yet

## Database choice
The repo root is Python and the UI lives in `frontend/`. The lowest-risk runtime foundation is still:
- SQL-first schema at repo root
- shared `DATABASE_URL` / `DATABASE_URL_POOLED` contract for Python + Next.js
- a pragmatic Python `psycopg` store boundary now
- future Drizzle adoption only when the frontend starts owning richer DB reads/mutations

## Current worker shape
### Market data
- polls on candle-aligned cadence
- fetches only recent closed candles
- updates in-memory freshness state
- writes worker heartbeat/status only
- does **not** persist tick streams or candle snapshots to Neon

### Signals
- fetches recent closed candles on the same conservative cadence
- evaluates configured local strategy modules
- emits signal events only when state changes / dedupe permits
- flushes batched `signal_events` to Neon

### Ops
- writes batched/upserted `runtime_worker_status`
- keeps `/ops` future reads cheap and current-state-oriented

## Research/runtime alignment rule
When a strategy is promoted into runtime, its version record should carry forward the richer backtest evidence already emitted by this project, including:
- exchange / symbol / timeframe / engine
- configured vs actual date range
- bar count
- fees / slippage
- entry / exit signal counts
- total return / max drawdown / sharpe / win rate / trade count
- notes

That keeps runtime promotion grounded in actual research evidence instead of a thin summary.

## Cadence rule of thumb
- wake workers on a simple interval, but only **write** when a fresh closed candle actually matters
- treat `signal_events` as append-only state-change records, not a tick stream
- batch heartbeats and non-critical worker stats in small batches
- keep frontend/runtime reads on aggregated views or read-model-friendly queries where possible

The point is simple: Neon should store operational truth, not every twitch of the market.
