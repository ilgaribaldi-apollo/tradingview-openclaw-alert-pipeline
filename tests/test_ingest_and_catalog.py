from __future__ import annotations

from pathlib import Path

from tv_indicators.intake import ingest_indicator
from tv_indicators.models import AnalysisRecord, IndicatorMetadata
from tv_indicators.paths import ANALYSIS_DIR, METADATA_DIR, RAW_DIR


def test_ingest_creates_expected_artifacts(tmp_path, monkeypatch):
    from tv_indicators import io as io_module

    monkeypatch.setattr(io_module, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(io_module, "METADATA_DIR", tmp_path / "metadata")
    monkeypatch.setattr(io_module, "ANALYSIS_DIR", tmp_path / "analysis")
    monkeypatch.setattr(io_module, "CATALOG_DIR", tmp_path / "catalog")

    metadata = IndicatorMetadata(
        slug="test-indicator",
        title="Test Indicator",
        author="Tester",
        source_url="https://example.com",
        discovered_from="Top",
        extracted_at="2026-03-14T00:00:00Z",
        pine_version="v5",
        script_type="indicator",
        classification="signal_capable",
    )
    analysis = AnalysisRecord(
        slug="test-indicator",
        summary="Test summary",
        signal_model="event_based",
    )

    result = ingest_indicator(metadata=metadata, source_code="//@version=5", analysis=analysis)
    assert Path(result["source_path"]).exists()
    assert Path(result["metadata_path"]).exists()
    assert Path(result["catalog_path"]).exists()
    assert Path(result["analysis_path"]).exists()
