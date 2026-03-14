from __future__ import annotations

import argparse
import json
from pathlib import Path

from .frontend_index import export_frontend_indexes
from .intake import ingest_indicator
from .io import read_yaml
from .models import AnalysisRecord, IndicatorMetadata


def main() -> None:
    parser = argparse.ArgumentParser(prog="tvir")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw Pine source + metadata")
    ingest_parser.add_argument("--metadata", required=True, help="Path to metadata YAML")
    ingest_parser.add_argument("--source", required=True, help="Path to raw Pine source")
    ingest_parser.add_argument("--analysis", help="Optional path to analysis YAML")

    backtest_parser = subparsers.add_parser("backtest", help="Run one indicator backtest")
    backtest_parser.add_argument("slug", help="Indicator slug")
    backtest_parser.add_argument("--config", default="default-matrix.yaml")
    backtest_parser.add_argument("--exchange", default="binance")
    backtest_parser.add_argument("--symbol")
    backtest_parser.add_argument("--timeframe")

    batch_parser = subparsers.add_parser("batch", help="Run a batch of indicators")
    batch_parser.add_argument("--config", default="default-matrix.yaml")
    batch_parser.add_argument("--exchange", default="binance")
    batch_parser.add_argument(
        "--status",
        action="append",
        help="Only run indicators with matching metadata status; can be passed multiple times",
    )

    frontend_parser = subparsers.add_parser(
        "export-frontend", help="Export normalized indexes for the Next.js observability app"
    )
    frontend_parser.add_argument(
        "--pretty",
        action="store_true",
        help="No-op placeholder for future formatting flags; exports are always pretty JSON",
    )

    args = parser.parse_args()
    if args.command == "ingest":
        metadata = IndicatorMetadata(**read_yaml(Path(args.metadata)))
        source_code = Path(args.source).read_text(encoding="utf-8")
        analysis = AnalysisRecord(**read_yaml(Path(args.analysis))) if args.analysis else None
        result = ingest_indicator(metadata=metadata, source_code=source_code, analysis=analysis)
    elif args.command == "backtest":
        from .backtest import run_indicator_backtest

        result = run_indicator_backtest(
            indicator_slug=args.slug,
            config_name=args.config,
            exchange=args.exchange,
            symbol=args.symbol,
            timeframe=args.timeframe,
        )
    elif args.command == "batch":
        from .batch import run_batch

        result = run_batch(
            statuses=set(args.status) if args.status else None,
            config_name=args.config,
            exchange=args.exchange,
        )
    else:
        result = export_frontend_indexes()
    print(json.dumps(result, indent=2))
