# Runtime Foundation — Sprint 2

This sprint adds the structural base for the runtime lane without changing current research/backtesting behavior.

## What was added
- `runtime/` folder scaffold for worker/config/service boundaries
- `db/` folder scaffold with an initial Neon/Postgres schema snapshot
- `api/` folder scaffold for shared runtime/webhook contracts

## What was deliberately not added
- no live execution code
- no broker credentials
- no active webhook server
- no runtime worker process implementation yet

## Database choice
The repo root is Python and the UI lives in `frontend/`. For now, the lowest-risk foundation is:
- SQL-first schema at repo root
- shared `DATABASE_URL`/Neon contract for Python + Next.js
- future Drizzle adoption only when the frontend actually starts querying/mutating runtime tables

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
