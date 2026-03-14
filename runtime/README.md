# Runtime Foundation

This directory holds the **paper-trading runtime lane** foundation.

## Scope right now
- runtime configuration templates
- real worker runner entrypoints in Python
- shared cadence / dedupe / heartbeat services
- adapter boundaries for market data and local strategy evaluation
- Neon/Postgres store boundary for runtime state
- non-durable local caches only

## Explicit non-goals
- no live order execution
- no broker/exchange write paths
- no paper executor yet
- no webhook server yet
- no process supervisor/orchestrator yet

## Layout
- `configs/` — runtime config + env examples
- `workers/market_data/` — candle freshness lane docs/placeholders
- `workers/signals/` — strategy evaluation lane docs/placeholders
- `workers/paper/` — paper-trading lane placeholder only
- `workers/ops/` — heartbeat/lag lane docs/placeholders
- `services/` — cadence, dedupe, buffering helpers
- `adapters/` — exchange / strategy / future webhook boundaries
- `state/` — non-durable local caches only

## Current CLI entrypoints
From the project root:

```bash
tvir runtime worker market-data --config runtime.example.yaml --once
tvir runtime worker signals --config runtime.example.yaml --once
tvir runtime worker ops --config runtime.example.yaml --once
```

Read-model helpers for future `/signals` and `/ops` work:

```bash
tvir runtime read-model signals --config runtime.example.yaml --limit 20
tvir runtime read-model ops --config runtime.example.yaml --limit 20
```

## Cadence model
- poll market data on a **candle-aligned cadence**, not on every tiny price move
- evaluate signals from closed candles only
- write `signal_events` only on **state changes / deduped triggers**
- batch/upsert worker heartbeats instead of writing every sample
- keep frontend reads on aggregated/read-model-friendly SQL views where possible

Research artifacts remain file-based under `indicators/`, `backtests/`, and `results/`. Operational state belongs in Neon/Postgres under `db/`.
