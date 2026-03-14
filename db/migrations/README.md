# Migrations

Sprint 2 uses ordered SQL schema files in `db/schema/`.

Suggested operator flow:
1. provision Neon database/branch
2. apply `db/schema/0001_runtime_foundation.sql`
3. optionally apply read models from `db/queries/runtime_read_models.sql`
4. add future numbered schema snapshots as the runtime gains real workers

If the frontend later adopts Drizzle, generated migrations can live here without changing the database contract layout.
