from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDICATORS_DIR = PROJECT_ROOT / "indicators"
RAW_DIR = INDICATORS_DIR / "raw"
METADATA_DIR = INDICATORS_DIR / "metadata"
ANALYSIS_DIR = INDICATORS_DIR / "analysis"
NORMALIZED_DIR = INDICATORS_DIR / "normalized"
STRATEGIES_DIR = INDICATORS_DIR / "strategies"
CATALOG_DIR = INDICATORS_DIR / "catalog"
DATA_DIR = PROJECT_ROOT / "data"
MARKET_DATA_DIR = DATA_DIR / "market"
BACKTESTS_DIR = PROJECT_ROOT / "backtests"
RESULTS_DIR = PROJECT_ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
RANKINGS_DIR = RESULTS_DIR / "rankings"
DOCS_DIR = PROJECT_ROOT / "docs"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_CONFIGS_DIR = RUNTIME_DIR / "configs"
DB_DIR = PROJECT_ROOT / "db"
