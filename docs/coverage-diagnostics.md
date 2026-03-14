# Coverage Diagnostics

## Purpose
Configured backtest range and realized history range are not the same thing unless the data provider actually supplies the full requested period.

## Required fields
Every run should record:
- `configured_start`
- `configured_end`
- `actual_start`
- `actual_end`
- `bar_count`
- `coverage_status`
- `coverage_complete`
- `coverage_gap_days`

## Interpretation
- `coverage_complete=true` means realized history reached the configured end date.
- `coverage_complete=false` means the run is based on incomplete history and should not be treated as a full-horizon result.
- `coverage_gap_days` shows how far short the realized end date is from the configured end date.

## Ranking rule
If coverage is incomplete, rankings and candidate assessments should surface that explicitly and lower confidence accordingly.
