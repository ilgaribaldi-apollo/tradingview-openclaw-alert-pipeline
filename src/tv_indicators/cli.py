from __future__ import annotations

import argparse
from pathlib import Path

from .frontend_index import export_frontend_indexes
from .intake import ingest_indicator
from .io import dumps_json, read_yaml
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
    backtest_parser.add_argument("--exchange")
    backtest_parser.add_argument("--symbol")
    backtest_parser.add_argument("--timeframe")

    batch_parser = subparsers.add_parser("batch", help="Run a batch of indicators")
    batch_parser.add_argument("--config", default="default-matrix.yaml")
    batch_parser.add_argument("--exchange")
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
    frontend_parser.add_argument(
        "--runtime-config",
        default="runtime.example.yaml",
        help="Runtime config used for optional Neon read-model snapshots",
    )

    runtime_parser = subparsers.add_parser(
        "runtime",
        help="Run runtime workers or inspect Neon read models",
    )
    runtime_subparsers = runtime_parser.add_subparsers(
        dest="runtime_command",
        required=True,
    )

    runtime_worker_parser = runtime_subparsers.add_parser(
        "worker",
        help="Run a runtime worker lane",
    )
    runtime_worker_parser.add_argument("lane", choices=["market-data", "signals", "ops"])
    runtime_worker_parser.add_argument("--config", default="runtime.example.yaml")
    runtime_worker_parser.add_argument(
        "--once",
        action="store_true",
        help="Run one iteration and flush",
    )
    runtime_worker_parser.add_argument(
        "--iterations",
        type=int,
        help="Optional bounded iteration count for non-once runs",
    )

    runtime_read_model_parser = runtime_subparsers.add_parser(
        "read-model", help="Inspect read-model-friendly runtime queries"
    )
    runtime_read_model_parser.add_argument("view", choices=["signals", "ops"])
    runtime_read_model_parser.add_argument("--config", default="runtime.example.yaml")
    runtime_read_model_parser.add_argument("--limit", type=int, default=20)

    runtime_promote_parser = runtime_subparsers.add_parser(
        "promote",
        help="Promote one backtested strategy version into the runtime registry",
    )
    runtime_promote_parser.add_argument("slug", help="Indicator/strategy slug")
    runtime_promote_parser.add_argument("--run-id", required=True)
    runtime_promote_parser.add_argument("--version", required=True)
    runtime_promote_parser.add_argument(
        "--verdict",
        default="paper_trade_candidate",
        choices=[
            "reject",
            "keep_researching",
            "paper_trade_candidate",
            "paper_trading",
            "live_candidate",
            "live_shadow",
            "live_enabled",
        ],
    )
    runtime_promote_parser.add_argument("--rationale", required=True)
    runtime_promote_parser.add_argument("--actor", default="apollo")
    runtime_promote_parser.add_argument("--owner")
    runtime_promote_parser.add_argument("--config", default="runtime.example.yaml")

    args = parser.parse_args()
    if args.command == "ingest":
        metadata = IndicatorMetadata(**read_yaml(Path(args.metadata)))
        source_code = Path(args.source).read_text(encoding="utf-8")
        analysis = AnalysisRecord(**read_yaml(Path(args.analysis))) if args.analysis else None
        result = ingest_indicator(metadata=metadata, source_code=source_code, analysis=analysis)
        frontend = export_frontend_indexes()
        result = {**result, "frontend": frontend}
    elif args.command == "backtest":
        from .backtest import run_indicator_backtest

        result = run_indicator_backtest(
            indicator_slug=args.slug,
            config_name=args.config,
            exchange=args.exchange,
            symbol=args.symbol,
            timeframe=args.timeframe,
        )
        frontend = export_frontend_indexes()
        result = {**result, "frontend": frontend}
    elif args.command == "batch":
        from .batch import run_batch

        batch_results = run_batch(
            statuses=set(args.status) if args.status else None,
            config_name=args.config,
            exchange=args.exchange,
        )
        frontend = export_frontend_indexes()
        result = {"items": batch_results, "frontend": frontend}
    elif args.command == "runtime":
        result = _run_runtime_command(args)
    else:
        result = export_frontend_indexes(runtime_config_name=args.runtime_config)
    print(dumps_json(result))


def _run_runtime_command(args: argparse.Namespace) -> object:
    from .runtime import (
        CCXTClosedCandlePoller,
        LocalStrategySignalEvaluator,
        MarketDataWorkerRunner,
        OpsWorkerRunner,
        PostgresRuntimeStore,
        RuntimeReadModelQueries,
        SignalWorkerRunner,
        build_strategy_promotion_payload,
        load_promoted_runtime_strategies,
        load_runtime_config,
    )

    config = load_runtime_config(args.config)
    store = PostgresRuntimeStore.from_database_config(config.database)

    if args.runtime_command == "read-model":
        queries = RuntimeReadModelQueries(store)
        if args.view == "signals":
            return queries.recent_signals(limit=args.limit)
        return queries.ops_overview(limit=args.limit)

    if args.runtime_command == "promote":
        payload = build_strategy_promotion_payload(
            slug=args.slug,
            run_id=args.run_id,
            version=args.version,
            verdict=args.verdict,
            rationale=args.rationale,
            actor=args.actor,
            owner=args.owner,
        )
        result = store.apply_strategy_promotion(payload)
        result["frontend"] = export_frontend_indexes(runtime_config_name=args.config)
        return result

    lane = args.lane
    if lane == "market-data":
        runner = MarketDataWorkerRunner(
            config=config,
            poller=CCXTClosedCandlePoller(),
            store=store,
        )
    elif lane == "signals":
        promoted_strategies = load_promoted_runtime_strategies(
            store.list_runtime_strategy_bindings()
        )
        if not promoted_strategies:
            raise RuntimeError(
                "No runtime-enabled promoted strategy bindings found. "
                "Run `tvir runtime promote ...` first."
            )
        runner = SignalWorkerRunner(
            config=config,
            poller=CCXTClosedCandlePoller(),
            evaluator=LocalStrategySignalEvaluator(strategies=promoted_strategies),
            store=store,
        )
    else:
        runner = OpsWorkerRunner(config=config, store=store)

    if args.once:
        return runner.run_once(force_flush=True)

    runner.run_forever(max_iterations=args.iterations)
    return {
        "lane": lane,
        "iterations": args.iterations,
        "status": "completed" if args.iterations is not None else "running",
    }
