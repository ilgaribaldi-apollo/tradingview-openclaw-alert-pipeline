# Neon Runtime Environment Notes

## Recommended environment variables
- `DATABASE_URL` — direct Neon Postgres connection for schema application and Python workers
- `DATABASE_URL_POOLED` — pooled Neon connection for serverless/frontend reads when needed
- `RUNTIME_ENV` — `development`, `staging`, or `production`
- `PAPER_TRADING_ENABLED` — keep `true` or `false` explicitly
- `LIVE_EXECUTION_ENABLED` — keep `false` in Sprint 2

## Safe defaults
- use separate Neon branches/databases for dev vs prod
- keep all credentials in `.env` or deploy secrets only
- never expose database URLs through `NEXT_PUBLIC_*`

## Applying the foundation schema
From the project root:

```bash
psql "$DATABASE_URL" -f db/schema/0001_runtime_foundation.sql
psql "$DATABASE_URL" -f db/queries/runtime_read_models.sql
```

You can also run the same SQL in the Neon SQL editor.

## Suggested usage split
- Python workers: `DATABASE_URL`
- Next.js server-side reads/API routes: `DATABASE_URL_POOLED` when serverless pooling matters
- local docs/examples: `runtime/configs/runtime.example.yaml`

## Current policy reminder
This environment is for research/runtime observability and paper trading only. Do not enable live execution from these settings.
