# Intake Workflow

## Purpose
Turn a TradingView script into a durable local research artifact.

## Steps
1. Use the TradingView skill to find a public indicator and open its source.
2. Create a slug for the indicator.
3. Save the exact source to `../indicators/raw/<slug>/source.pine`.
4. Create metadata at `../indicators/metadata/<slug>.yaml`.
5. Add or update a row in `../indicators/catalog/indicators.csv`.
6. Classify the script:
   - visual_only
   - signal_capable
   - strategy_native
   - ambiguous
   - repainting_risk
   - not_worth_testing
7. Decide whether to:
   - keep as catalog-only
   - normalize
   - adapt into strategy wrapper

## Minimum metadata
- slug
- title
- author
- source_url
- discovered_from
- extracted_at
- pine_version
- script_type
- classification
- status
- notes

## Non-negotiables
- Raw source is preserved exactly.
- Do not put adaptation notes inside the raw file.
- If source provenance is unclear, do not ingest it as a first-class artifact.
- After intake, follow `docs/workflow-blueprint.md` for analysis, translation, backtesting, and comparison.
