from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from tv_indicators.runtime.config import load_runtime_config
from tv_indicators.runtime.models import (
    MarketDataCadenceConfig,
    OpsHeartbeatConfig,
    SignalBatchingConfig,
    SignalEventCandidate,
    WorkerHeartbeatSample,
)
from tv_indicators.runtime.services import (
    CandleAlignedCadencePlanner,
    SignalEventBuffer,
    WorkerHeartbeatBuffer,
    build_signal_dedupe_key,
    timeframe_to_seconds,
)


class RecordingRuntimeStore:
    def __init__(self) -> None:
        self.signal_write_batches: list[list[SignalEventCandidate]] = []
        self.heartbeat_write_batches: list[list[WorkerHeartbeatSample]] = []

    def write_signal_events(self, events: list[SignalEventCandidate]) -> int:
        batch = list(events)
        self.signal_write_batches.append(batch)
        return len(batch)

    def write_worker_heartbeats(self, heartbeats: list[WorkerHeartbeatSample]) -> int:
        batch = list(heartbeats)
        self.heartbeat_write_batches.append(batch)
        return len(batch)


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


def make_signal_event(
    *,
    signal_type: str,
    state: str,
    signal_at: datetime,
    candle_close_at: datetime,
    price: float = 100000.0,
    strategy_version: str = "ema-cross@v1",
    venue: str = "coinbase",
    symbol: str = "BTC/USD",
    timeframe: str = "1h",
) -> SignalEventCandidate:
    return SignalEventCandidate(
        strategy_version=strategy_version,
        venue=venue,
        symbol=symbol,
        timeframe=timeframe,
        signal_type=signal_type,
        state=state,
        signal_at=signal_at,
        candle_close_at=candle_close_at,
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


def test_load_runtime_config_reads_cadence_and_batching_fields():
    config = load_runtime_config()

    assert config.database.provider == "neon_postgres"
    assert config.watchlist.exchange == "coinbase"
    assert config.watchlist_entries()[0].key == "coinbase:BTC/USD:1h"
    assert config.workers.market_data.cadence.align_to_candle_close is True
    assert config.workers.market_data.cadence.write_on_new_candle_only is True
    assert config.workers.signals.batching.emit_on_state_change_only is True
    assert config.workers.signals.batching.max_batch_size == 25
    assert config.workers.ops.heartbeat.flush_interval_seconds == 120


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
    next_candle = replace(base, signal_at=start + timedelta(hours=1), candle_close_at=start + timedelta(hours=1))
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
        signal_type="enter_long",
        state="long",
        signal_at=start,
        candle_close_at=start,
    )
    duplicate_state = make_signal_event(
        signal_type="enter_long",
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
    assert [event.signal_type for event in flushed] == ["enter_long", "exit_long"]
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
    assert [event.signal_type for event in store.signal_write_batches[0]] == ["entry_long", "exit_long"]


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
