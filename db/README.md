# Runtime Database Foundation

This project is currently a **Python repo with a separate Next.js frontend**. For Sprint 2, the pragmatic choice is:

- keep the first database foundation **SQL-first** at the repo root
- use **Neon/Postgres** as the operational store
- let both Python workers and the Next.js app share the same database contracts
- defer any Drizzle/frontend-specific wiring until runtime reads/writes actually land

Why this choice:
- avoids introducing a second root JS toolchain just to define tables
- keeps migrations runnable from Python/operator workflows with plain SQL
- still leaves the schema cleanly portable to Drizzle later from the `frontend/` side if desired

## Layout
- `schema/` — ordered SQL schema snapshots
- `queries/` — shared read-model SQL for dashboards and ops views
- `migrations/` — migration notes / future generated artifacts
- `seed/` — safe example seed/reference data
