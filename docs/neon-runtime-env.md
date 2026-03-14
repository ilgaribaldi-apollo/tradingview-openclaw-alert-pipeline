# Neon Runtime Environment Notes

## Recommended environment variables
- `DATABASE_URL` — direct Neon Postgres connection for schema application and Python workers
- `DATABASE_URL_POOLED` — pooled Neon connection for server-side/frontend reads when needed later
- `RUNTIME_ENV` — `development`, `staging`, or `production`
- `PAPER_TRADING_ENABLED` — keep `true` or `false` explicitly
- `LIVE_EXECUTION_ENABLED` — keep `false`

See `runtime/configs/runtime.env.example` for a safe example shape.

## Safe defaults
- use separate Neon branches/databases for dev vs prod
- keep all credentials in `.env` or deploy secrets only
- never expose database URLs through `NEXT_PUBLIC_*`
- prefer least-privilege DB roles for workers when practical

## Applying the schema + views
From the project root:

```bash
psql "$DATABASE_URL" -f db/schema/0001_runtime_foundation.sql
psql "$DATABASE_URL" -f db/queries/runtime_read_models.sql
```

You can also run the same SQL in the Neon SQL editor.

## Optional local bootstrap rows
For a safe dev bootstrap while the promotion lane is still file-first:

```bash
psql "$DATABASE_URL" -f db/seed/watchlist.example.sql
psql "$DATABASE_URL" -f db/seed/runtime_strategy.example.sql
```

That gives the signal worker a concrete watchlist row plus a pinned strategy/version row to resolve.

## Example runtime worker commands
```bash
tvir runtime worker market-data --config runtime.example.yaml --once
tvir runtime worker signals --config runtime.example.yaml --once
tvir runtime worker ops --config runtime.example.yaml --once
```

## Example read-model checks
```bash
tvir runtime read-model signals --config runtime.example.yaml --limit 20
tvir runtime read-model ops --config runtime.example.yaml --limit 20
```

## Suggested usage split
- Python workers: `DATABASE_URL`
- Next.js server-side reads/API routes: `DATABASE_URL_POOLED` when pooling matters
- local config/examples: `runtime/configs/runtime.example.yaml`

## Current policy reminder
This environment is for research/runtime observability and paper trading only.
Do not enable live execution from these settings.
