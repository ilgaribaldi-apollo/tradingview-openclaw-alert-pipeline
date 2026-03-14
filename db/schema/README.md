# Schema

`0001_runtime_foundation.sql` establishes the paper-trading runtime base tables only.

Design rules:
- keep research truth on disk
- keep operational state in Postgres
- include enough structure to audit promotions, signals, paper positions, and worker health
- preserve room for the richer backtest evidence already emitted by the research pipeline
