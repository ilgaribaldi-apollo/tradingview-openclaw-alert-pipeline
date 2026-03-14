from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from .models import AnalysisRecord, IndicatorMetadata
from .paths import ANALYSIS_DIR, CATALOG_DIR, METADATA_DIR, RAW_DIR


CATALOG_COLUMNS = [
    "slug",
    "title",
    "author",
    "source_url",
    "discovered_from",
    "extracted_at",
    "pine_version",
    "script_type",
    "classification",
    "repaint_risk",
    "status",
    "notes",
]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def sanitize_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return sanitize_json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (np.floating, float, Decimal)):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


def dumps_json(data: Any) -> str:
    return json.dumps(sanitize_json_value(data), indent=2, sort_keys=True, allow_nan=False)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(dumps_json(data), encoding="utf-8")


def save_raw_source(slug: str, source_code: str) -> Path:
    raw_dir = ensure_dir(RAW_DIR / slug)
    source_path = raw_dir / "source.pine"
    source_path.write_text(source_code, encoding="utf-8")
    return source_path


def save_metadata(metadata: IndicatorMetadata) -> Path:
    path = METADATA_DIR / f"{metadata.slug}.yaml"
    write_yaml(path, asdict(metadata))
    return path


def save_analysis(record: AnalysisRecord) -> Path:
    path = ANALYSIS_DIR / record.slug / "analysis.yaml"
    write_yaml(path, asdict(record))
    return path


def upsert_catalog(metadata: IndicatorMetadata) -> Path:
    ensure_dir(CATALOG_DIR)
    path = CATALOG_DIR / "indicators.csv"
    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
    row = {key: str(getattr(metadata, key, "")) for key in CATALOG_COLUMNS}
    replaced = False
    for idx, existing in enumerate(rows):
        if existing.get("slug") == metadata.slug:
            rows[idx] = row
            replaced = True
            break
    if not replaced:
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
