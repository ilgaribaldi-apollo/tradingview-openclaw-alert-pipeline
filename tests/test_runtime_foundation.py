from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
    timeframe_to_seconds,
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

    first = SignalEventCandidate(
        strategy_version="ema-cross@v1",
        venue="coinbase",
        symbol="BTC/USD",
        timeframe="1h",
        signal_type="enter_long",
        state="long",
        signal_at=start,
        candle_close_at=start,
        price=100000.0,
    )
    duplicate_state = SignalEventCandidate(
        strategy_version="ema-cross@v1",
        venue="coinbase",
        symbol="BTC/USD",
        timeframe="1h",
        signal_type="enter_long",
        state="long",
        signal_at=start + timedelta(minutes=1),
        candle_close_at=start + timedelta(hours=1),
        price=100100.0,
    )
    exit_signal = SignalEventCandidate(
        strategy_version="ema-cross@v1",
        venue="coinbase",
        symbol="BTC/USD",
        timeframe="1h",
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
