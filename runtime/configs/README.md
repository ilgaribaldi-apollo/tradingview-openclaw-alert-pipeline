# Runtime Configs

Configuration files here should be **checked-in templates only**.

## Rules
- store secrets in environment variables, never in YAML
- keep live execution disabled unless a later explicitly approved sprint changes that
- pin watchlists/timeframes deliberately so paper runs are auditable
- mirror the richer backtest schema fields when carrying research evidence into runtime
- prefer candle-aligned polling over per-tick ingestion
- persist signal events only for state changes / deduped triggers
- batch heartbeats and non-critical stats before writing them to Neon
