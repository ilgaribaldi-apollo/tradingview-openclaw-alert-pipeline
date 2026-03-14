from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .interfaces import MarketDataPoller, RuntimeStore, SignalEvaluator
from .models import (
    MarketDataWorkerRunResult,
    OpsWorkerRunResult,
    RuntimeConfig,
    SignalWorkerRunResult,
    WatchlistEntry,
    WorkerHeartbeatSample,
)
from .services import (
    CandleAlignedCadencePlanner,
    SignalEventBuffer,
    WorkerHeartbeatBuffer,
    timeframe_to_seconds,
)


@dataclass(slots=True)
class MarketDataWorkerState:
    last_polled_at_by_watchlist: dict[str, datetime] = field(default_factory=dict)
    last_completed_candle_at_by_watchlist: dict[str, datetime] = field(default_factory=dict)
    latest_candles_by_watchlist: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


@dataclass(slots=True)
class SignalWorkerState:
    last_polled_at_by_watchlist: dict[str, datetime] = field(default_factory=dict)
    last_evaluated_candle_at_by_watchlist: dict[str, datetime] = field(default_factory=dict)


class MarketDataWorkerRunner:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        poller: MarketDataPoller,
        store: RuntimeStore | None,
        state: MarketDataWorkerState | None = None,
        heartbeat_buffer: WorkerHeartbeatBuffer | None = None,
    ) -> None:
        self.config = config
        self.poller = poller
        self.store = store
        self.state = state or MarketDataWorkerState()
        self.planner = CandleAlignedCadencePlanner(config.workers.market_data.cadence)
        self.heartbeat_buffer = heartbeat_buffer or WorkerHeartbeatBuffer(
            config.workers.ops.heartbeat,
            initial_now=datetime.now(UTC),
        )

    def run_once(
        self,
        *,
        now: datetime | None = None,
        force_flush: bool = False,
    ) -> MarketDataWorkerRunResult:
        current = _as_utc(now or datetime.now(UTC))
        due_watchlists = 0
        refreshed_watchlists = 0
        latest: dict[str, datetime] = {}
        errors: list[str] = []
        max_lag: int | None = None

        for watchlist in self.config.watchlist_entries():
            decision = self.planner.should_poll(
                now=current,
                timeframe=watchlist.timeframe,
                last_completed_candle_at=self.state.last_completed_candle_at_by_watchlist.get(watchlist.key),
                last_polled_at=self.state.last_polled_at_by_watchlist.get(watchlist.key),
            )
            if not decision.due:
                continue
            due_watchlists += 1
            self.state.last_polled_at_by_watchlist[watchlist.key] = current
            try:
                candles = list(
                    self.poller.fetch_closed_candles(
                        watchlist=watchlist,
                        limit=self.config.workers.market_data.fetch_limit,
                    )
                )
                if not candles:
                    continue
                latest_candle_close_at = _latest_candle_close_at(candles, watchlist=watchlist)
                self.state.latest_candles_by_watchlist[watchlist.key] = candles
                self.state.last_completed_candle_at_by_watchlist[
                    watchlist.key
                ] = latest_candle_close_at
                latest[watchlist.key] = latest_candle_close_at
                refreshed_watchlists += 1
                lag_seconds = max(0, int((current - latest_candle_close_at).total_seconds()))
                max_lag = lag_seconds if max_lag is None else max(max_lag, lag_seconds)
            except Exception as exc:
                errors.append(f"{watchlist.key}: {exc}")

        heartbeat_rows_written = _record_and_flush_heartbeat(
            store=self.store,
            buffer=self.heartbeat_buffer,
            sample=WorkerHeartbeatSample(
                worker_name=self.config.workers.market_data.worker_name,
                lane="market_data",
                status="degraded" if errors else "running",
                heartbeat_at=current,
                lag_seconds=max_lag,
                stats={
                    "due_watchlists": due_watchlists,
                    "refreshed_watchlists": refreshed_watchlists,
                    "cached_watchlists": len(self.state.latest_candles_by_watchlist),
                },
                error_summary="; ".join(errors[:3]) or None,
            ),
            now=current,
            force_flush=force_flush,
        )

        return MarketDataWorkerRunResult(
            due_watchlists=due_watchlists,
            refreshed_watchlists=refreshed_watchlists,
            latest_candle_close_at_by_watchlist=latest,
            heartbeat_rows_written=heartbeat_rows_written,
        )

    def run_forever(self, *, max_iterations: int | None = None) -> None:
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            self.run_once()
            iterations += 1
            time.sleep(self.config.workers.market_data.cadence.poll_seconds)


class SignalWorkerRunner:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        poller: MarketDataPoller,
        evaluator: SignalEvaluator,
        store: RuntimeStore | None,
        state: SignalWorkerState | None = None,
        signal_buffer: SignalEventBuffer | None = None,
        heartbeat_buffer: WorkerHeartbeatBuffer | None = None,
    ) -> None:
        self.config = config
        self.poller = poller
        self.evaluator = evaluator
        self.store = store
        self.state = state or SignalWorkerState()
        self.planner = CandleAlignedCadencePlanner(config.workers.signals.cadence)
        self.signal_buffer = signal_buffer or SignalEventBuffer(
            config.workers.signals.batching,
            initial_now=datetime.now(UTC),
        )
        self.heartbeat_buffer = heartbeat_buffer or WorkerHeartbeatBuffer(
            config.workers.ops.heartbeat,
            initial_now=datetime.now(UTC),
        )

    def run_once(
        self,
        *,
        now: datetime | None = None,
        force_flush: bool = False,
    ) -> SignalWorkerRunResult:
        current = _as_utc(now or datetime.now(UTC))
        due_watchlists = 0
        evaluated_watchlists = 0
        accepted_events = 0
        max_lag: int | None = None
        errors: list[str] = []

        for watchlist in self.config.watchlist_entries():
            decision = self.planner.should_poll(
                now=current,
                timeframe=watchlist.timeframe,
                last_completed_candle_at=self.state.last_evaluated_candle_at_by_watchlist.get(watchlist.key),
                last_polled_at=self.state.last_polled_at_by_watchlist.get(watchlist.key),
            )
            if not decision.due:
                continue
            due_watchlists += 1
            self.state.last_polled_at_by_watchlist[watchlist.key] = current
            try:
                candles = list(
                    self.poller.fetch_closed_candles(
                        watchlist=watchlist,
                        limit=self.config.workers.signals.candle_limit,
                    )
                )
                if not candles:
                    continue
                latest_candle_close_at = _latest_candle_close_at(candles, watchlist=watchlist)
                lag_seconds = max(0, int((current - latest_candle_close_at).total_seconds()))
                max_lag = lag_seconds if max_lag is None else max(max_lag, lag_seconds)
                candidates = list(self.evaluator.evaluate(watchlist=watchlist, candles=candles))
                for candidate in candidates:
                    if self.signal_buffer.add(candidate):
                        accepted_events += 1
                evaluated_watchlists += 1
                self.state.last_evaluated_candle_at_by_watchlist[
                    watchlist.key
                ] = latest_candle_close_at
            except Exception as exc:
                errors.append(f"{watchlist.key}: {exc}")

        persisted_events = 0
        if self.store is not None:
            batch = self.signal_buffer.flush_due(now=current, force=force_flush)
            if batch:
                persisted_events = self.store.write_signal_events(batch)
        elif force_flush:
            self.signal_buffer.flush_due(now=current, force=True)

        heartbeat_rows_written = _record_and_flush_heartbeat(
            store=self.store,
            buffer=self.heartbeat_buffer,
            sample=WorkerHeartbeatSample(
                worker_name=self.config.workers.signals.worker_name,
                lane="signals",
                status="degraded" if errors else "running",
                heartbeat_at=current,
                lag_seconds=max_lag,
                stats={
                    "due_watchlists": due_watchlists,
                    "evaluated_watchlists": evaluated_watchlists,
                    "accepted_events": accepted_events,
                    "persisted_events": persisted_events,
                    "pending_events": self.signal_buffer.pending_count,
                },
                error_summary="; ".join(errors[:3]) or None,
            ),
            now=current,
            force_flush=force_flush,
        )

        return SignalWorkerRunResult(
            due_watchlists=due_watchlists,
            evaluated_watchlists=evaluated_watchlists,
            accepted_events=accepted_events,
            persisted_events=persisted_events,
            pending_events=self.signal_buffer.pending_count,
            heartbeat_rows_written=heartbeat_rows_written,
        )

    def run_forever(self, *, max_iterations: int | None = None) -> None:
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            self.run_once()
            iterations += 1
            time.sleep(self.config.workers.signals.cadence.poll_seconds)


class OpsWorkerRunner:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        store: RuntimeStore | None,
        heartbeat_buffer: WorkerHeartbeatBuffer | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.heartbeat_buffer = heartbeat_buffer or WorkerHeartbeatBuffer(
            config.workers.ops.heartbeat,
            initial_now=datetime.now(UTC),
        )

    def run_once(
        self,
        *,
        now: datetime | None = None,
        force_flush: bool = False,
        stats: dict[str, Any] | None = None,
        error_summary: str | None = None,
        status: str = "running",
    ) -> OpsWorkerRunResult:
        current = _as_utc(now or datetime.now(UTC))
        written = _record_and_flush_heartbeat(
            store=self.store,
            buffer=self.heartbeat_buffer,
            sample=WorkerHeartbeatSample(
                worker_name=self.config.workers.ops.worker_name,
                lane="ops",
                status=status,
                heartbeat_at=current,
                stats=stats or {},
                error_summary=error_summary,
            ),
            now=current,
            force_flush=force_flush,
        )
        return OpsWorkerRunResult(
            pending_heartbeats=self.heartbeat_buffer.pending_count,
            heartbeat_rows_written=written,
        )

    def run_forever(self, *, max_iterations: int | None = None) -> None:
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            self.run_once()
            iterations += 1
            time.sleep(self.config.workers.ops.heartbeat.collect_seconds)


def _latest_candle_close_at(
    candles: list[dict[str, Any]],
    *,
    watchlist: WatchlistEntry,
) -> datetime:
    latest = candles[-1]
    explicit = latest.get("candle_close_at")
    if isinstance(explicit, datetime):
        return _as_utc(explicit)
    open_at = latest.get("candle_open_at") or latest.get("open_time")
    if isinstance(open_at, datetime):
        return _as_utc(open_at) + timedelta(
            seconds=timeframe_to_seconds(watchlist.timeframe)
        )
    raise ValueError(
        f"Latest candle payload for {watchlist.key} is missing candle_close_at/open_time"
    )


def _record_and_flush_heartbeat(
    *,
    store: RuntimeStore | None,
    buffer: WorkerHeartbeatBuffer,
    sample: WorkerHeartbeatSample,
    now: datetime,
    force_flush: bool,
) -> int:
    buffer.record(sample)
    if store is None:
        if force_flush:
            buffer.flush_due(now=now, force=True)
        return 0
    batch = buffer.flush_due(now=now, force=force_flush)
    if not batch:
        return 0
    return store.write_worker_heartbeats(batch)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
