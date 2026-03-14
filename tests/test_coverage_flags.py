from __future__ import annotations

from tv_indicators.backtest import _coverage_status


def test_coverage_status_marks_incomplete_when_actual_end_far_before_configured_end():
    status = _coverage_status(
        configured_start="2023-01-01",
        configured_end="2026-01-01",
        actual_start="2023-01-01T00:00:00+00:00",
        actual_end="2023-03-17T00:00:00+00:00",
    )
    assert status["coverage_complete"] is False
    assert status["coverage_status"] == "incomplete"
    assert status["coverage_gap_days"] is not None and status["coverage_gap_days"] > 900


def test_coverage_status_marks_complete_when_actual_range_matches_end():
    status = _coverage_status(
        configured_start="2023-01-01",
        configured_end="2023-01-31",
        actual_start="2023-01-01T00:00:00+00:00",
        actual_end="2023-01-31T00:00:00+00:00",
    )
    assert status["coverage_complete"] is True
    assert status["coverage_status"] == "complete"
    assert status["coverage_gap_days"] == 0
