# Reusable Filter / Exit Packs

## Purpose
Keep experiments composable instead of rewriting the same trade-management logic in every `logic.py`.

## Filter packs
Stored under:
- `backtests/configs/filters/`

Current examples:
- `above-ema-200.yaml`
- `min-atr-pct-1.yaml`

Filters are applied to **entries** after the base experiment signal logic runs.

## Exit packs
Stored under:
- `backtests/configs/exits/`

Current examples:
- `opposite-signal.yaml`
- `time-stop-48-bars.yaml`

Exit packs are applied to **exits** after the base experiment signal logic runs.

## Current implementation scope
Right now this layer supports:
- `above_ema`
- `min_atr_percent`
- `opposite_signal` (pass-through semantic marker)
- `time_stop_bars` (documented placeholder for future stateful runner support)

## Why this matters
This lets us define experiments like:
- base signal: RSI 30/70
- filters: `above-ema-200`
- exits: `opposite-signal`

instead of duplicating trend-filter and exit logic across dozens of variants.
