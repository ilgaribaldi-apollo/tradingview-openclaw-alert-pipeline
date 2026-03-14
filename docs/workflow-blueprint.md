# Workflow Blueprint — TradingView Skill -> Python Backtest

## Purpose
This is the operator runbook for the full indicator research loop:
1. find an indicator in TradingView
2. extract Pine source
3. ingest it into the project
4. analyze and classify it
5. translate it into Python strategy logic
6. run a backtest
7. save and compare results
8. export normalized frontend indexes
9. inspect the results in the Next.js observability app

## Core rule
- **TradingView is for discovery and source extraction.**
- **Python is for analysis, translation, backtesting, comparison, and frontend index export.**
- **Next.js is for observability, not for becoming the source of truth.**

Do not use TradingView Strategy Tester as the main research engine for this workflow.

---

## Phase 1: Discover and extract with the TradingView skill

### Goal
Capture a public indicator and preserve its exact Pine source.

### Steps
1. Open TradingView chart.
2. Open **Indicators, metrics, and strategies**.
3. Browse **Editors' picks**, **Top**, or **Trending**.
4. Hover the target row.
5. Click the **code/source** icon.
6. Extract the full Pine script.
7. Record:
   - indicator title
   - author
   - TradingView URL
   - discovery section
   - Pine version if visible

### Output
Prepare three local files before ingestion:
- `source.pine`
- `metadata.yaml`
- optional `analysis.yaml`

---

## Phase 2: Ingest into the project

### Goal
Save the indicator as a first-class research artifact.

### File destinations
- raw source -> `indicators/raw/<slug>/source.pine`
- metadata -> `indicators/metadata/<slug>.yaml`
- analysis -> `indicators/analysis/<slug>/analysis.yaml`
- catalog row -> `indicators/catalog/indicators.csv`

### CLI
```bash
tvir ingest --metadata path/to/metadata.yaml --source path/to/source.pine --analysis path/to/analysis.yaml
```

### Minimum metadata status values
Recommended lifecycle:
- `raw_only`
- `analyzed`
- `strategy_ready`
- `benchmarked`
- `rejected`
- `promoted`

---

## Phase 3: Analyze before translating

### Goal
Decide whether the script is actually worth converting.

### Questions
- Is this visual-only or signal-capable?
- Are entries/exits explicit or ambiguous?
- Any repaint risk?
- Any multi-timeframe or TradingView-only behavior?
- Can the core logic map cleanly to Python?

### Output
Create/update `analysis.yaml` with:
- summary
- signal model
- inputs
- features
- unsupported features
- entry logic
- exit logic
- caution flags
- translation notes

If the script is junk or too ambiguous, mark it `rejected` and stop.

---

## Phase 4: Translate into Python strategy logic

### Goal
Create a Python strategy wrapper that preserves the usable signal semantics.

### Destination
- `indicators/strategies/<slug>/logic.py`
- `indicators/strategies/<slug>/NOTES.md`

### Rules
- Do not edit raw Pine.
- Translate signal logic, not charts or visuals.
- Document assumptions explicitly.
- Keep strategy wrappers boring and readable.

### Required function
Each strategy wrapper must expose:
```python
def generate_signals(df):
    ...
    return df
```

Expected columns:
- `entry`
- `exit`

---

## Phase 5: Run the backtest

### Goal
Run the strategy on a standardized dataset and save immutable outputs.

### Default assumptions
- exchange: `coinbase`
- symbols: default crypto basket in `backtests/configs/default-matrix.yaml`
- timeframe: `1h`
- config: `backtests/configs/default-matrix.yaml`

### CLI
```bash
tvir backtest <slug> --config default-matrix.yaml --exchange coinbase --symbol BTC/USD --timeframe 1h
```

### Outputs
Each run creates:
- `results/runs/<run-id>/config.yaml`
- `results/runs/<run-id>/metrics.json`
- `results/runs/<run-id>/trades.csv`
- `results/runs/<run-id>/summary.md`

It also updates:
- `results/rankings/leaderboard.csv`

---

## Phase 6: Batch compare many indicators

### Goal
Run only indicators that are actually ready.

### Rule
Only batch indicators whose metadata status is `strategy_ready`.

### CLI
```bash
tvir batch --status strategy_ready --config default-matrix.yaml --exchange coinbase
```

### Outputs
- successful runs append to `results/rankings/leaderboard.csv`
- failures append to `results/rankings/failed_runs.csv`
- frontend generated indexes refresh automatically for observability

---

## Phase 7: Export frontend indexes

### Goal
Generate the normalized JSON artifacts that the Next.js observability app reads.

### Rule
The frontend should read generated index files, not scrape raw Pine files or crawl the run directories directly in the browser.

### CLI
```bash
tvir export-frontend
```

### Outputs
This exports normalized artifacts to:
- `frontend/src/generated/dashboard-summary.json`
- `frontend/src/generated/indicators-index.json`
- `frontend/src/generated/coverage-matrix.json`
- `frontend/src/generated/rankings-index.json`
- `frontend/src/generated/runs-index.json`

### Required behavior
- keep Python artifacts as the source of truth
- regenerate indexes after new ingest/backtest activity
- align the rankings export with the current leaderboard schema (`exchange`, `symbol`, `timeframe`, `engine`, metrics)

---

## Phase 8: Inspect in the frontend

### Goal
Use the observability app to inspect the pipeline without losing provenance.

### App surfaces
- `/` — dashboard overview
- `/indicators` — catalog inventory
- `/indicators/[slug]` — per-indicator state and run history
- `/coverage` — pair/timeframe coverage matrix
- `/rankings` — leaderboard plus caveats and failures
- `/runs/[runId]` — run-level assumptions and summary

### Deployment note
The frontend is intended for Vercel deployment from `project/frontend/`.
Generated JSON indexes should be present in the app tree at build time.

---

## Decision rules

### Promote
If an indicator:
- survives translation cleanly
- produces understandable behavior
- performs reasonably under the benchmark matrix
- does not rely on bullshit/repainting

mark it for deeper study or promotion.

### Reject
If an indicator is:
- mostly visual fluff
- too ambiguous to translate honestly
- overly repaint-prone
- weak under reasonable assumptions

mark it `rejected` and move on.

---

## What is ready right now
The project is ready for:
- ingestion
- metadata/cataloging
- analysis storage
- Python strategy wrappers
- single backtest runs
- batch backtest orchestration
- result persistence and comparison tables
- frontend index export
- Next.js observability UI over indicators, coverage, rankings, and runs

## What is not fully ready yet
Still rough / placeholder:
- no auto-converter from Pine to Python
- no advanced report generation yet
- some TradingView source extractions may still be partial/truncated for larger scripts and need extractor hardening

So the honest answer is:
**the system is structurally ready to test, but it needs the first real indicator pushed through the pipeline to validate the workflow.**

---

## Recommended first validation
1. pick one simple public indicator
2. extract Pine source with the TradingView skill
3. ingest it
4. create analysis
5. translate to Python
6. run one `coinbase` `BTC/USD` `1h` backtest
7. export frontend indexes with `tvir export-frontend`
8. inspect `/rankings`, `/coverage`, and `/runs/[runId]` in the frontend
9. fix any rough edges before scaling to a batch
