# Runtime Foundation

This directory holds the **paper-trading runtime lane** scaffolding for Sprint 2.

## Scope right now
- runtime configuration templates
- worker lane boundaries
- shared runtime service boundaries
- adapter boundaries for future external inputs
- ephemeral local state only

## Explicit non-goals
- no live order execution
- no broker/exchange write paths
- no runtime process manager yet

## Layout
- `configs/` — runtime config templates and promotion/paper-trading defaults
- `workers/market_data/` — candle ingestion/update lane
- `workers/signals/` — strategy evaluation + signal emission lane
- `workers/paper/` — paper-trading execution lane only
- `workers/ops/` — heartbeat/lag/incident lane
- `services/` — shared dedupe/promotion/read-model services
- `adapters/` — external signal/input boundaries (for example TradingView alerts later)
- `state/` — non-durable local caches only

Research artifacts remain file-based under `indicators/`, `backtests/`, and `results/`. Operational state belongs in Neon/Postgres under `db/`.
