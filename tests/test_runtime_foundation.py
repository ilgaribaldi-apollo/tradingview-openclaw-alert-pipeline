from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

from tv_indicators.runtime.adapters import LocalStrategySignalEvaluator
from tv_indicators.runtime.config import load_runtime_config
from tv_indicators.runtime.models import (
    MarketDataCadenceConfig,
    MarketDataWorkerConfig,
    OpsHeartbeatConfig,
    OpsWorkerConfig,
    PaperWorkerConfig,
    RuntimeConfig,
    RuntimeDatabaseConfig,
    RuntimeModeConfig,
    RuntimeSourceOfTruth,
    RuntimeStrategyConfig,
    RuntimeWorkersConfig,
    SignalBatchingConfig,
    SignalCadenceConfig,
    SignalEventCandidate,
    SignalWorkerConfig,
    WatchlistConfig,
    WorkerHeartbeatSample,
)
from tv_indicators.runtime.read_models import RuntimeReadModelQueries
from tv_indicators.runtime.runners import (
    MarketDataWorkerRunner,
    OpsWorkerRunner,
    SignalWorkerRunner,
)
from tv_indicators.runtime.services import (
    CandleAlignedCadencePlanner,
    SignalEventBuffer,
    WorkerHeartbeatBuffer,
    build_signal_dedupe_key,
    timeframe_to_seconds,
)
from tv_indicators.runtime.store import PostgresRuntimeStore, RuntimeStoreError


class RecordingRuntimeStore:
    def __init__(self) -> None:
        self.signal_write_batches: list[list[SignalEventCandidate]] = []
        self.heartbeat_write_batches: list[list[WorkerHeartbeatSample]] = []
        self.signal_feed_rows: list[dict[str, Any]] = []
        self.ops_rows: list[dict[str, Any]] = []

    def write_signal_events(self, events: list[SignalEventCandidate]) -> int:
        batch = list(events)
        self.signal_write_batches.append(batch)
        return len(batch)

    def write_worker_heartbeats(self, heartbeats: list[WorkerHeartbeatSample]) -> int:
        batch = list(heartbeats)
        self.heartbeat_write_batches.append(batch)
        return len(batch)

    def list_recent_signal_feed(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self.signal_feed_rows[:limit]

    def list_runtime_ops_overview(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self.ops_rows[:limit]


class StaticPoller:
    def __init__(self, candles_by_watchlist: dict[str, list[dict[str, Any]]]) -> None:
        self.candles_by_watchlist = candles_by_watchlist
        self.calls: list[tuple[str, int | None]] = []

    def fetch_closed_candles(self, *, watchlist, limit: int | None = None):
        self.calls.append((watchlist.key, limit))
        return list(self.candles_by_watchlist.get(watchlist.key, []))


class StaticEvaluator:
    def __init__(self, events_by_watchlist: dict[str, list[SignalEventCandidate]]) -> None:
        self.events_by_watchlist = events_by_watchlist
        self.calls: list[str] = []

    def evaluate(self, *, watchlist, candles):
        self.calls.append(watchlist.key)
        return list(self.events_by_watchlist.get(watchlist.key, []))


class FakeDatabaseHarness:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[Any] | None]] = []
        self.watchlist_ids: dict[tuple[str, str, str], str] = {}
        self.strategy_version_ids: dict[tuple[str, str], str] = {}
        self.signal_insert_returning: list[tuple[Any, ...]] = []
        self.heartbeat_insert_returning: list[tuple[Any, ...]] = []
        self.signal_feed_rows: list[dict[str, Any]] = []
        self.ops_rows: list[dict[str, Any]] = []
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    def connection_factory(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, harness: FakeDatabaseHarness) -> None:
        self.harness = harness

    def cursor(self):
        return FakeCursor(self.harness)

    def commit(self) -> None:
        self.harness.commit_count += 1

    def rollback(self) -> None:
        self.harness.rollback_count += 1

    def close(self) -> None:
        self.harness.close_count += 1


class FakeCursor:
    def __init__(self, harness: FakeDatabaseHarness) -> None:
        self.harness = harness
        self._fetchone: Any = None
        self._fetchall: list[Any] = []
        self.description: list[Any] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: list[Any] | None = None) -> None:
        normalized = " ".join(sql.split())
        self.harness.calls.append((normalized, list(params) if params is not None else None))
        self._fetchone = None
        self._fetchall = []
        self.description = []

        if normalized.startswith("insert into symbol_watchlists"):
            key = (str(params[0]), str(params[1]), str(params[2]))
            identifier = self.harness.watchlist_ids.setdefault(
                key,
                f"watchlist-{len(self.harness.watchlist_ids) + 1}",
            )
            self._fetchone = (identifier,)
            self.description = [("id",)]
            return
        if normalized.startswith("select sv.id"):
            key = (str(params[0]), str(params[1]))
            identifier = self.harness.strategy_version_ids.get(key)
            self._fetchone = None if identifier is None else (identifier,)
            self.description = [("id",)]
            return
        if normalized.startswith("insert into signal_events"):
            self._fetchall = list(self.harness.signal_insert_returning)
            self.description = [("dedupe_key",)]
            return
        if normalized.startswith("insert into runtime_worker_status"):
            self._fetchall = list(self.harness.heartbeat_insert_returning)
            self.description = [("worker_name",), ("lane",)]
            return
        if "from runtime_signal_feed" in normalized:
            self._fetchall = list(self.harness.signal_feed_rows)
            return
        if "from runtime_ops_overview" in normalized:
            self._fetchall = list(self.harness.ops_rows)
            return

        raise AssertionError(f"Unhandled SQL in fake cursor: {normalized}")

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return list(self._fetchall)


def flush_signal_buffer_to_store(
    store: RecordingRuntimeStore,
    buffer: SignalEventBuffer,
    *,
    now: datetime,
    force: bool = False,
) -> int:
    batch = buffer.flush_due(now=now, force=force)
    if not batch:
        return 0
    return store.write_signal_events(batch)


def flush_heartbeat_buffer_to_store(
    store: RecordingRuntimeStore,
    buffer: WorkerHeartbeatBuffer,
    *,
    now: datetime,
    force: bool = False,
) -> int:
    batch = buffer.flush_due(now=now, force=force)
    if not batch:
        return 0
    return store.write_worker_heartbeats(batch)


def make_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        environment="test",
        database=RuntimeDatabaseConfig(provider="neon_postgres", url_env="DATABASE_URL"),
        runtime=RuntimeModeConfig(
            paper_trading_enabled=True,
            live_execution_enabled=False,
            source_of_truth=RuntimeSourceOfTruth(
                research_artifacts="results/",
                operational_state="neon",
            ),
        ),
        watchlist=WatchlistConfig(exchange="coinbase", symbols=["BTC/USD"], timeframes=["1h"]),
        workers=RuntimeWorkersConfig(
            market_data=MarketDataWorkerConfig(
                enabled=True,
                worker_name="market_data",
                fetch_limit=10,
                cadence=MarketDataCadenceConfig(
                    poll_seconds=60,
                    align_to_candle_close=True,
                    write_on_new_candle_only=True,
                    lag_tolerance_seconds=15,
                ),
            ),
            signals=SignalWorkerConfig(
                enabled=True,
                worker_name="signals",
                candle_limit=10,
                cadence=SignalCadenceConfig(
                    poll_seconds=60,
                    align_to_candle_close=True,
                    evaluate_on_new_candle_only=True,
                    lag_tolerance_seconds=15,
                ),
                batching=SignalBatchingConfig(
                    emit_on_state_change_only=True,
                    dedupe_window_seconds=3600,
                    flush_interval_seconds=30,
                    max_batch_size=25,
                ),
            ),
            paper=PaperWorkerConfig(enabled=True, worker_name="paper"),
            ops=OpsWorkerConfig(
                enabled=True,
                worker_name="ops",
                heartbeat=OpsHeartbeatConfig(
                    collect_seconds=30,
                    flush_interval_seconds=60,
                    max_batch_size=10,
                    include_stats=True,
                ),
            ),
        ),
        strategies=[
            RuntimeStrategyConfig(
                slug="strategy-rsi",
                version="local-v1",
                minimum_candles=2,
                watchlist_keys=["coinbase:BTC/USD:1h"],
                signal_columns={"entry_long": "entry", "exit_long": "exit"},
            )
        ],
    )


def make_signal_event(
    *,
    signal_type: str,
    state: str,
    signal_at: datetime,
    candle_close_at: datetime,
    price: float = 100000.0,
    strategy_slug: str = "strategy-rsi",
    strategy_version: str = "local-v1",
    venue: str = "coinbase",
    symbol: str = "BTC/USD",
    timeframe: str = "1h",
) -> SignalEventCandidate:
    return SignalEventCandidate(
        strategy_slug=strategy_slug,
        strategy_version=strategy_version,
        venue=venue,
        symbol=symbol,
        timeframe=timeframe,
        signal_type=signal_type,
        signal_at=signal_at,
        candle_open_at=candle_close_at - timedelta(hours=1),
        candle_close_at=candle_close_at,
        state=state,
        price=price,
    )


def make_heartbeat(
    *,
    worker_name: str,
    lane: str,
    heartbeat_at: datetime,
    lag_seconds: int,
    status: str = "ok",
    stats: dict[str, int] | None = None,
) -> WorkerHeartbeatSample:
    return WorkerHeartbeatSample(
        worker_name=worker_name,
        lane=lane,
        status=status,
        heartbeat_at=heartbeat_at,
        lag_seconds=lag_seconds,
        stats=stats or {},
    )


def make_candles(*, start: datetime, count: int, timeframe_hours: int = 1) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for index in range(count):
        candle_open_at = start + timedelta(hours=index * timeframe_hours)
        candle_close_at = candle_open_at + timedelta(hours=timeframe_hours)
        candles.append(
            {
                "candle_open_at": candle_open_at,
                "candle_close_at": candle_close_at,
                "open": 100.0 + index,
                "high": 101.0 + index,
                "low": 99.0 + index,
                "close": 100.5 + index,
                "volume": 10.0 + index,
            }
        )
    return candles


def test_load_runtime_config_reads_cadence_batching_and_strategy_fields():
    config = load_runtime_config()

    assert config.database.provider == "neon_postgres"
    assert config.watchlist.exchange == "coinbase"
    assert config.watchlist_entries()[0].key == "coinbase:BTC/USD:1h"
    assert config.workers.market_data.worker_name == "market_data"
    assert config.workers.market_data.fetch_limit == 250
    assert config.workers.market_data.cadence.align_to_candle_close is True
    assert config.workers.signals.worker_name == "signals"
    assert config.workers.signals.candle_limit == 250
    assert config.workers.signals.batching.emit_on_state_change_only is True
    assert config.workers.ops.worker_name == "ops"
    assert config.workers.ops.heartbeat.flush_interval_seconds == 120
    assert config.enabled_strategies()[0].identity_key == "strategy-rsi@local-v1"


def test_timeframe_to_seconds_supports_common_units():
    assert timeframe_to_seconds("1m") == 60
    assert timeframe_to_seconds("15m") == 900
    assert timeframe_to_seconds("1h") == 3600
    assert timeframe_to_seconds("1d") == 86400


def test_timeframe_to_seconds_rejects_invalid_values():
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        timeframe_to_seconds("1")

    with pytest.raises(ValueError, match="Unsupported timeframe unit"):
        timeframe_to_seconds("5x")

    with pytest.raises(ValueError, match="Timeframe magnitude must be positive"):
        timeframe_to_seconds("0m")


def test_candle_planner_waits_for_closed_candle_and_lag():
    planner = CandleAlignedCadencePlanner(
        MarketDataCadenceConfig(
            poll_seconds=60,
            align_to_candle_close=True,
            write_on_new_candle_only=True,
            lag_tolerance_seconds=15,
        )
    )

    just_after_close = datetime(2026, 3, 14, 15, 0, 10, tzinfo=UTC)
    before_lag = planner.should_poll(
        now=just_after_close,
        timeframe="1h",
        last_completed_candle_at=datetime(2026, 3, 14, 14, 0, tzinfo=UTC),
        last_polled_at=datetime(2026, 3, 14, 14, 30, tzinfo=UTC),
    )
    assert before_lag.due is False
    assert before_lag.reason == "awaiting_candle_close_lag"

    after_lag = planner.should_poll(
        now=datetime(2026, 3, 14, 15, 0, 20, tzinfo=UTC),
        timeframe="1h",
        last_completed_candle_at=datetime(2026, 3, 14, 14, 0, tzinfo=UTC),
        last_polled_at=datetime(2026, 3, 14, 14, 30, tzinfo=UTC),
    )
    assert after_lag.due is True
    assert after_lag.reason == "new_closed_candle_ready"
    assert after_lag.candle_close_at == datetime(2026, 3, 14, 15, 0, tzinfo=UTC)

    already_done = planner.should_poll(
        now=datetime(2026, 3, 14, 15, 1, 0, tzinfo=UTC),
        timeframe="1h",
        last_completed_candle_at=datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
        last_polled_at=datetime(2026, 3, 14, 15, 0, 20, tzinfo=UTC),
    )
    assert already_done.due is False
    assert already_done.reason == "latest_closed_candle_already_processed"


def test_candle_planner_respects_minimum_poll_interval_after_close():
    planner = CandleAlignedCadencePlanner(
        MarketDataCadenceConfig(
            poll_seconds=300,
            align_to_candle_close=True,
            write_on_new_candle_only=True,
            lag_tolerance_seconds=15,
        )
    )

    decision = planner.should_poll(
        now=datetime(2026, 3, 14, 15, 10, tzinfo=UTC),
        timeframe="1h",
        last_completed_candle_at=datetime(2026, 3, 14, 14, 0, tzinfo=UTC),
        last_polled_at=datetime(2026, 3, 14, 15, 8, tzinfo=UTC),
    )

    assert decision.due is False
    assert decision.reason == "minimum_poll_interval_not_elapsed"
    assert decision.next_poll_at == datetime(2026, 3, 14, 15, 13, tzinfo=UTC)
    assert decision.candle_close_at == datetime(2026, 3, 14, 15, 0, tzinfo=UTC)


def test_build_signal_dedupe_key_ignores_tick_noise_but_changes_for_new_state_boundary():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    base = make_signal_event(
        signal_type="entry_long",
        state="long",
        signal_at=start,
        candle_close_at=start,
        price=100000.0,
    )
    tick_noise = replace(
        base,
        signal_at=start + timedelta(seconds=10),
        price=100050.0,
        context={"tick": 2, "note": "same closed candle, same state"},
    )
    next_candle = replace(
        base,
        signal_at=start + timedelta(hours=1),
        candle_close_at=start + timedelta(hours=1),
    )
    exit_signal = replace(base, signal_type="exit_long", state="flat")

    assert build_signal_dedupe_key(base) == build_signal_dedupe_key(tick_noise)
    assert build_signal_dedupe_key(base) != build_signal_dedupe_key(next_candle)
    assert build_signal_dedupe_key(base) != build_signal_dedupe_key(exit_signal)


def test_signal_event_buffer_only_enqueues_state_changes_and_flushes_in_batches():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    buffer = SignalEventBuffer(
        SignalBatchingConfig(
            emit_on_state_change_only=True,
            dedupe_window_seconds=3600,
            flush_interval_seconds=120,
            max_batch_size=2,
        ),
        initial_now=start,
    )

    first = make_signal_event(
        signal_type="entry_long",
        state="long",
        signal_at=start,
        candle_close_at=start,
    )
    duplicate_state = make_signal_event(
        signal_type="entry_long",
        state="long",
        signal_at=start + timedelta(minutes=1),
        candle_close_at=start + timedelta(hours=1),
        price=100100.0,
    )
    exit_signal = make_signal_event(
        signal_type="exit_long",
        state="flat",
        signal_at=start + timedelta(hours=2),
        candle_close_at=start + timedelta(hours=2),
        price=100050.0,
    )

    assert buffer.add(first) is True
    assert buffer.add(duplicate_state) is False
    assert buffer.add(exit_signal) is True
    assert buffer.pending_count == 2

    flushed = buffer.flush_due(now=start + timedelta(minutes=2))
    assert len(flushed) == 2
    assert [event.signal_type for event in flushed] == ["entry_long", "exit_long"]
    assert buffer.pending_count == 0


def test_signal_buffer_avoids_per_tick_store_writes_for_unchanged_state():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    store = RecordingRuntimeStore()
    buffer = SignalEventBuffer(
        SignalBatchingConfig(
            emit_on_state_change_only=True,
            dedupe_window_seconds=3600,
            flush_interval_seconds=300,
            max_batch_size=10,
        ),
        initial_now=start,
    )

    accepted = []
    for minute in range(5):
        current = start + timedelta(minutes=minute)
        accepted.append(
            buffer.add(
                make_signal_event(
                    signal_type="entry_long",
                    state="long",
                    signal_at=current,
                    candle_close_at=current,
                    price=100000.0 + minute,
                )
            )
        )
        assert flush_signal_buffer_to_store(store, buffer, now=current) == 0

    assert accepted == [True, False, False, False, False]
    assert buffer.pending_count == 1
    assert store.signal_write_batches == []

    assert flush_signal_buffer_to_store(store, buffer, now=start + timedelta(minutes=5)) == 1
    assert len(store.signal_write_batches) == 1
    assert len(store.signal_write_batches[0]) == 1
    assert store.signal_write_batches[0][0].signal_type == "entry_long"


def test_signal_buffer_flushes_to_store_when_batch_size_is_reached():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    store = RecordingRuntimeStore()
    buffer = SignalEventBuffer(
        SignalBatchingConfig(
            emit_on_state_change_only=True,
            dedupe_window_seconds=3600,
            flush_interval_seconds=3600,
            max_batch_size=2,
        ),
        initial_now=start,
    )

    first = make_signal_event(
        signal_type="entry_long",
        state="long",
        signal_at=start,
        candle_close_at=start,
    )
    second = make_signal_event(
        signal_type="exit_long",
        state="flat",
        signal_at=start + timedelta(minutes=1),
        candle_close_at=start + timedelta(minutes=1),
    )

    assert buffer.add(first) is True
    assert flush_signal_buffer_to_store(store, buffer, now=start) == 0

    assert buffer.add(second) is True
    assert flush_signal_buffer_to_store(store, buffer, now=start + timedelta(minutes=1)) == 2
    assert len(store.signal_write_batches) == 1
    assert [event.signal_type for event in store.signal_write_batches[0]] == [
        "entry_long",
        "exit_long",
    ]


def test_worker_heartbeat_buffer_keeps_latest_per_worker_and_flushes_on_interval():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    buffer = WorkerHeartbeatBuffer(
        OpsHeartbeatConfig(
            collect_seconds=30,
            flush_interval_seconds=60,
            max_batch_size=10,
            include_stats=True,
        ),
        initial_now=start,
    )

    buffer.record(
        WorkerHeartbeatSample(
            worker_name="market-data-1",
            lane="market_data",
            status="ok",
            heartbeat_at=start,
            lag_seconds=5,
            stats={"symbols": 4},
        )
    )
    buffer.record(
        WorkerHeartbeatSample(
            worker_name="market-data-1",
            lane="market_data",
            status="ok",
            heartbeat_at=start + timedelta(seconds=30),
            lag_seconds=2,
            stats={"symbols": 4},
        )
    )
    buffer.record(
        WorkerHeartbeatSample(
            worker_name="signal-worker-1",
            lane="signals",
            status="ok",
            heartbeat_at=start + timedelta(seconds=30),
            lag_seconds=1,
            stats={"pendingSignals": 0},
        )
    )

    assert buffer.flush_due(now=start + timedelta(seconds=59)) == []

    flushed = buffer.flush_due(now=start + timedelta(seconds=61))
    assert len(flushed) == 2
    latest_market = [item for item in flushed if item.worker_name == "market-data-1"][0]
    assert latest_market.lag_seconds == 2
    assert buffer.pending_count == 0


def test_heartbeat_buffer_batches_latest_samples_into_one_store_write():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    store = RecordingRuntimeStore()
    buffer = WorkerHeartbeatBuffer(
        OpsHeartbeatConfig(
            collect_seconds=30,
            flush_interval_seconds=120,
            max_batch_size=10,
            include_stats=True,
        ),
        initial_now=start,
    )

    samples = [
        make_heartbeat(
            worker_name="market-data-1",
            lane="market_data",
            heartbeat_at=start,
            lag_seconds=5,
            stats={"symbols": 4},
        ),
        make_heartbeat(
            worker_name="market-data-1",
            lane="market_data",
            heartbeat_at=start + timedelta(seconds=30),
            lag_seconds=3,
            stats={"symbols": 4},
        ),
        make_heartbeat(
            worker_name="signal-worker-1",
            lane="signals",
            heartbeat_at=start + timedelta(seconds=60),
            lag_seconds=1,
            stats={"pendingSignals": 0},
        ),
    ]

    for sample in samples:
        buffer.record(sample)
        assert flush_heartbeat_buffer_to_store(store, buffer, now=sample.heartbeat_at) == 0

    assert store.heartbeat_write_batches == []
    assert buffer.pending_count == 2

    assert flush_heartbeat_buffer_to_store(store, buffer, now=start + timedelta(seconds=121)) == 2
    assert len(store.heartbeat_write_batches) == 1
    assert [(item.lane, item.worker_name) for item in store.heartbeat_write_batches[0]] == [
        ("market_data", "market-data-1"),
        ("signals", "signal-worker-1"),
    ]
    latest_market = store.heartbeat_write_batches[0][0]
    assert latest_market.lag_seconds == 3


def test_heartbeat_buffer_flushes_to_store_when_batch_size_is_reached():
    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    store = RecordingRuntimeStore()
    buffer = WorkerHeartbeatBuffer(
        OpsHeartbeatConfig(
            collect_seconds=30,
            flush_interval_seconds=600,
            max_batch_size=2,
            include_stats=True,
        ),
        initial_now=start,
    )

    buffer.record(
        make_heartbeat(
            worker_name="market-data-1",
            lane="market_data",
            heartbeat_at=start,
            lag_seconds=4,
        )
    )
    assert flush_heartbeat_buffer_to_store(store, buffer, now=start) == 0

    buffer.record(
        make_heartbeat(
            worker_name="signal-worker-1",
            lane="signals",
            heartbeat_at=start + timedelta(seconds=30),
            lag_seconds=1,
        )
    )
    assert flush_heartbeat_buffer_to_store(store, buffer, now=start + timedelta(seconds=30)) == 2
    assert len(store.heartbeat_write_batches) == 1
    assert len(store.heartbeat_write_batches[0]) == 2


def test_local_strategy_signal_evaluator_emits_candidates_for_latest_closed_candle():
    now = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    candles = make_candles(start=now - timedelta(hours=2), count=2)

    def module_loader(_: str):
        def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            df["entry"] = [False, True]
            df["exit"] = [False, False]
            return df

        return SimpleNamespace(generate_signals=generate_signals)

    evaluator = LocalStrategySignalEvaluator(
        strategies=[
            RuntimeStrategyConfig(
                slug="strategy-rsi",
                version="local-v1",
                minimum_candles=2,
                watchlist_keys=["coinbase:BTC/USD:1h"],
                signal_columns={"entry_long": "entry", "exit_long": "exit"},
            )
        ],
        module_loader=module_loader,
    )

    events = evaluator.evaluate(
        watchlist=make_runtime_config().watchlist_entries()[0],
        candles=candles,
    )

    assert len(events) == 1
    event = events[0]
    assert event.strategy_slug == "strategy-rsi"
    assert event.strategy_version == "local-v1"
    assert event.signal_type == "entry_long"
    assert event.state == "long"
    assert event.candle_close_at == candles[-1]["candle_close_at"]


def test_market_data_worker_runner_refreshes_once_and_persists_heartbeat():
    config = make_runtime_config()
    now = datetime(2026, 3, 14, 15, 0, 20, tzinfo=UTC)
    candles = make_candles(start=datetime(2026, 3, 14, 13, 0, tzinfo=UTC), count=2)
    poller = StaticPoller({"coinbase:BTC/USD:1h": candles})
    store = RecordingRuntimeStore()
    runner = MarketDataWorkerRunner(config=config, poller=poller, store=store)

    result = runner.run_once(now=now, force_flush=True)

    assert result.due_watchlists == 1
    assert result.refreshed_watchlists == 1
    assert result.heartbeat_rows_written == 1
    assert poller.calls == [("coinbase:BTC/USD:1h", 10)]
    assert len(store.heartbeat_write_batches) == 1
    heartbeat = store.heartbeat_write_batches[0][0]
    assert heartbeat.lane == "market_data"
    assert heartbeat.stats["refreshed_watchlists"] == 1

    second = runner.run_once(now=now + timedelta(seconds=10), force_flush=True)
    assert second.due_watchlists == 0
    assert poller.calls == [("coinbase:BTC/USD:1h", 10)]


def test_signal_worker_runner_persists_signal_events_and_heartbeat_on_force_flush():
    config = make_runtime_config()
    now = datetime(2026, 3, 14, 15, 0, 20, tzinfo=UTC)
    candles = make_candles(start=datetime(2026, 3, 14, 13, 0, tzinfo=UTC), count=2)
    event = make_signal_event(
        signal_type="entry_long",
        state="long",
        signal_at=candles[-1]["candle_close_at"],
        candle_close_at=candles[-1]["candle_close_at"],
    )
    poller = StaticPoller({"coinbase:BTC/USD:1h": candles})
    evaluator = StaticEvaluator({"coinbase:BTC/USD:1h": [event]})
    store = RecordingRuntimeStore()
    runner = SignalWorkerRunner(config=config, poller=poller, evaluator=evaluator, store=store)

    result = runner.run_once(now=now, force_flush=True)

    assert result.due_watchlists == 1
    assert result.evaluated_watchlists == 1
    assert result.accepted_events == 1
    assert result.persisted_events == 1
    assert result.pending_events == 0
    assert result.heartbeat_rows_written == 1
    assert len(store.signal_write_batches) == 1
    assert store.signal_write_batches[0][0].strategy_slug == "strategy-rsi"
    assert len(store.heartbeat_write_batches) == 1
    heartbeat = store.heartbeat_write_batches[0][0]
    assert heartbeat.lane == "signals"
    assert heartbeat.stats["persisted_events"] == 1


def test_ops_worker_runner_batches_and_flushes_its_own_status():
    config = make_runtime_config()
    store = RecordingRuntimeStore()
    runner = OpsWorkerRunner(config=config, store=store)
    now = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)

    result = runner.run_once(now=now, force_flush=True, stats={"workers": 2})

    assert result.pending_heartbeats == 0
    assert result.heartbeat_rows_written == 1
    assert len(store.heartbeat_write_batches) == 1
    heartbeat = store.heartbeat_write_batches[0][0]
    assert heartbeat.lane == "ops"
    assert heartbeat.stats == {"workers": 2}


def test_postgres_runtime_store_batches_signal_events_and_reuses_resolution_cache():
    harness = FakeDatabaseHarness()
    harness.watchlist_ids[("coinbase", "BTC/USD", "1h")] = "watch-1"
    harness.strategy_version_ids[("strategy-rsi", "local-v1")] = "sv-1"
    harness.signal_insert_returning = [("key-1",), ("key-2",)]
    store = PostgresRuntimeStore(harness.connection_factory)

    start = datetime(2026, 3, 14, 15, 0, tzinfo=UTC)
    inserted = store.write_signal_events(
        [
            make_signal_event(
                signal_type="entry_long",
                state="long",
                signal_at=start,
                candle_close_at=start,
            ),
            make_signal_event(
                signal_type="exit_long",
                state="flat",
                signal_at=start + timedelta(hours=1),
                candle_close_at=start + timedelta(hours=1),
            ),
        ]
    )

    assert inserted == 2
    assert harness.commit_count == 1
    assert harness.rollback_count == 0
    assert harness.close_count == 1
    watchlist_resolution_calls = [
        call for call, _ in harness.calls if call.startswith("insert into symbol_watchlists")
    ]
    strategy_resolution_calls = [
        call for call, _ in harness.calls if call.startswith("select sv.id")
    ]
    signal_insert_calls = [
        params for call, params in harness.calls if call.startswith("insert into signal_events")
    ]
    assert len(watchlist_resolution_calls) == 1
    assert len(strategy_resolution_calls) == 1
    assert len(signal_insert_calls) == 1
    assert len(signal_insert_calls[0]) == 20


def test_postgres_runtime_store_raises_for_missing_strategy_binding():
    harness = FakeDatabaseHarness()
    harness.watchlist_ids[("coinbase", "BTC/USD", "1h")] = "watch-1"
    store = PostgresRuntimeStore(harness.connection_factory)

    with pytest.raises(RuntimeStoreError, match="Strategy version row not found"):
        store.write_signal_events(
            [
                make_signal_event(
                    signal_type="entry_long",
                    state="long",
                    signal_at=datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
                    candle_close_at=datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
                )
            ]
        )

    assert harness.rollback_count == 1
    assert harness.close_count == 1


def test_postgres_runtime_store_upserts_heartbeats_and_read_models():
    harness = FakeDatabaseHarness()
    harness.heartbeat_insert_returning = [("signals", "signals"), ("ops", "ops")]
    harness.signal_feed_rows = [
        {
            "id": "sig-1",
            "signal_at": datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
            "strategy_slug": "strategy-rsi",
            "strategy_title": "Strategy RSI",
            "venue": "coinbase",
            "symbol": "BTC/USD",
            "timeframe": "1h",
            "signal_type": "entry_long",
            "signal_source": "local_evaluator",
            "price": 101.25,
            "dedupe_key": "dedupe-1",
            "context": {"foo": "bar"},
            "strategy_version": "local-v1",
        }
    ]
    harness.ops_rows = [
        {
            "worker_name": "signals",
            "lane": "signals",
            "status": "running",
            "heartbeat_at": datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
            "lag_seconds": 5,
            "error_summary": None,
            "tracked_feeds": 1,
        }
    ]
    store = PostgresRuntimeStore(harness.connection_factory)

    written = store.write_worker_heartbeats(
        [
            make_heartbeat(
                worker_name="signals",
                lane="signals",
                heartbeat_at=datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
                lag_seconds=5,
                status="running",
                stats={"pending_events": 0},
            ),
            make_heartbeat(
                worker_name="ops",
                lane="ops",
                heartbeat_at=datetime(2026, 3, 14, 15, 0, tzinfo=UTC),
                lag_seconds=0,
                status="running",
                stats={"workers": 2},
            ),
        ]
    )

    assert written == 2
    queries = RuntimeReadModelQueries(store)
    signals = queries.recent_signals(limit=10)
    ops_rows = queries.ops_overview(limit=10)

    assert signals[0].strategy_slug == "strategy-rsi"
    assert signals[0].dedupe_key == "dedupe-1"
    assert ops_rows[0].worker_name == "signals"
    assert ops_rows[0].tracked_feeds == 1
