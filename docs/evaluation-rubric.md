# Evaluation Rubric

## Primary questions
1. Is the script actually testable?
2. If testable, what assumptions must be added?
3. Does it hold up under a standardized test matrix?
4. Is the result robust or just cosmetically impressive?

## Classification cues
### visual_only
- mostly plotting zones, labels, or discretionary context
- no clear mechanical entry/exit logic

### signal_capable
- exposes conditions that can plausibly become explicit rules
- still needs wrapper logic

### strategy_native
- already contains strategy semantics or close equivalents

### ambiguous
- logic unclear, subjective, or too open to interpretation

### repainting_risk
- uses lookahead-style logic, future-dependent constructs, or suspiciously perfect signals

### not_worth_testing
- low information value, poor code quality, or redundant with better scripts

## Baseline evaluation dimensions
- net return
- max drawdown
- profit factor
- win rate
- trade count
- stability across symbols/timeframes
- sensitivity to fees/slippage
- sensitivity to small parameter shifts

## Decision-quality additions
Every serious indicator review should also answer:
- **Why does it rank well?**
- **Where does it break?**
- **Is the edge broad or narrow?**
- **Is the logic interpretable enough for live monitoring?**
- **What would disqualify it quickly?**

Recommended derived fields:
- `overall_score`
- `confidence_score`
- `robustness_score`
- `live_readiness_score`
- `strengths`
- `weaknesses`
- `failure_modes`
- `next_tests`
- `verdict`

Recommended verdicts:
- `reject`
- `keep_researching`
- `paper_trade_candidate`
- `paper_trading`
- `live_candidate`

## Rule
A pretty chart is not evidence. Comparable outputs are evidence.
A high return with weak reasoning is not a top candidate.
