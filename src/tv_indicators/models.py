from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class IndicatorMetadata:
    slug: str
    title: str
    author: str
    source_url: str
    discovered_from: str
    extracted_at: str
    pine_version: str
    script_type: str
    classification: str
    repaint_risk: str = "unknown"
    status: str = "raw_only"
    tags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(slots=True)
class AnalysisRecord:
    slug: str
    summary: str
    signal_model: str
    inputs: dict[str, Any] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    entry_logic: str = ""
    exit_logic: str = ""
    caution_flags: list[str] = field(default_factory=list)
    translation_notes: str = ""


@dataclass(slots=True)
class ExperimentSpec:
    experiment_slug: str
    title: str
    family: str
    variant: str
    indicators: list[str] = field(default_factory=list)
    kind: str = "variant"
    status: str = "draft"
    logic_path: str = "logic.py"
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    filters: list[str] = field(default_factory=list)
    exits: list[str] = field(default_factory=list)
    matrix: str = "default-matrix.yaml"
    horizons: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(slots=True)
class TestMatrix:
    name: str
    symbols: list[str]
    timeframes: list[str]
    date_range: dict[str, str]
    fees_bps: float
    slippage_bps: float
    position_sizing: str
    notes: str = ""
    default_exchange: str = "coinbase"


@dataclass(slots=True)
class BacktestRunResult:
    indicator_slug: str
    run_id: str
    metrics: dict[str, Any]
    trades_path: Path
    summary_path: Path
    config_path: Path
