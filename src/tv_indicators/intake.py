from __future__ import annotations

from .io import save_analysis, save_metadata, save_raw_source, upsert_catalog
from .models import AnalysisRecord, IndicatorMetadata


def ingest_indicator(
    *,
    metadata: IndicatorMetadata,
    source_code: str,
    analysis: AnalysisRecord | None = None,
) -> dict[str, str]:
    source_path = save_raw_source(metadata.slug, source_code)
    metadata_path = save_metadata(metadata)
    catalog_path = upsert_catalog(metadata)
    analysis_path = save_analysis(analysis) if analysis else None
    return {
        "source_path": str(source_path),
        "metadata_path": str(metadata_path),
        "catalog_path": str(catalog_path),
        "analysis_path": str(analysis_path) if analysis_path else "",
    }
