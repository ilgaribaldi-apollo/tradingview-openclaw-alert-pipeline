from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from ..io import sanitize_json_value
from .models import (
    MarketDataCadenceConfig,
    MarketDataPollDecision,
    OpsHeartbeatConfig,
    SignalBatchingConfig,
    SignalCadenceConfig,
    SignalEventCandidate,
    WorkerHeartbeatSample,
)

_TIMEFRAME_UNITS = {
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24,
    "w": 60 * 60 * 24 * 7,
}


def timeframe_to_seconds(timeframe: str) -> int:
    cleaned = timeframe.strip().lower()
    if len(cleaned) < 2:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    unit = cleaned[-1]
    multiplier = _TIMEFRAME_UNITS.get(unit)
    if multiplier is None:
        raise ValueError(f"Unsupported timeframe unit: {timeframe}")
    magnitude = int(cleaned[:-1])
    if magnitude <= 0:
        raise ValueError(f"Timeframe magnitude must be positive: {timeframe}")
    return magnitude * multiplier


class CandleAlignedCadencePlanner:
    def __init__(self, cadence: MarketDataCadenceConfig | SignalCadenceConfig) -> None:
        self.cadence = cadence

    def latest_closed_candle_at(self, *, now: datetime, timeframe: str) -> datetime:
        now_utc = _as_utc(now)
        interval = timeframe_to_seconds(timeframe)
        closed_ts = int(now_utc.timestamp()) // interval * interval
        return datetime.fromtimestamp(closed_ts, tz=UTC)

    def next_poll_at(self, *, now: datetime, timeframe: str) -> datetime:
        now_utc = _as_utc(now)
        interval = timeframe_to_seconds(timeframe)
        closed = self.latest_closed_candle_at(now=now_utc, timeframe=timeframe)
        next_close = closed + timedelta(seconds=interval)
        return next_close + timedelta(
            seconds=getattr(self.cadence, "lag_tolerance_seconds", 0)
        )

    def should_poll(
        self,
        *,
        now: datetime,
        timeframe: str,
        last_completed_candle_at: datetime | None = None,
        last_polled_at: datetime | None = None,
    ) -> MarketDataPollDecision:
        now_utc = _as_utc(now)
        latest_closed = self.latest_closed_candle_at(now=now_utc, timeframe=timeframe)
        available_at = latest_closed + timedelta(
            seconds=getattr(self.cadence, "lag_tolerance_seconds", 0)
        )
        next_poll_at = self.next_poll_at(now=now_utc, timeframe=timeframe)

        if getattr(self.cadence, "align_to_candle_close", True) and now_utc < available_at:
            return MarketDataPollDecision(
                due=False,
                reason="awaiting_candle_close_lag",
                next_poll_at=available_at,
                candle_close_at=latest_closed,
            )

        completed_utc = _as_utc(last_completed_candle_at) if last_completed_candle_at else None
        if completed_utc is not None and completed_utc >= latest_closed:
            return MarketDataPollDecision(
                due=False,
                reason="latest_closed_candle_already_processed",
                next_poll_at=next_poll_at,
                candle_close_at=latest_closed,
            )

        polled_utc = _as_utc(last_polled_at) if last_polled_at else None
        if polled_utc is not None:
            minimum_next_poll = polled_utc + timedelta(seconds=self.cadence.poll_seconds)
            if now_utc < minimum_next_poll:
                return MarketDataPollDecision(
                    due=False,
                    reason="minimum_poll_interval_not_elapsed",
                    next_poll_at=minimum_next_poll,
                    candle_close_at=latest_closed,
                )

        return MarketDataPollDecision(
            due=True,
            reason="new_closed_candle_ready",
            next_poll_at=next_poll_at,
            candle_close_at=latest_closed,
        )


class SignalEventBuffer:
    def __init__(
        self,
        config: SignalBatchingConfig,
        *,
        initial_now: datetime | None = None,
    ) -> None:
        self.config = config
        self._buffer: list[SignalEventCandidate] = []
        self._last_state_by_identity: dict[str, str] = {}
        self._dedupe_expiry_by_key: dict[str, datetime] = {}
        self._last_flush_at = _as_utc(initial_now or datetime.now(UTC))

    @property
    def pending_count(self) -> int:
        return len(self._buffer)

    def add(self, event: SignalEventCandidate) -> bool:
        event_time = _as_utc(event.signal_at)
        self._expire_dedupe_keys(event_time)

        dedupe_key = build_signal_dedupe_key(event)
        fingerprint = _signal_state_fingerprint(event)
        previous_fingerprint = self._last_state_by_identity.get(event.identity_key)
        if self.config.emit_on_state_change_only and previous_fingerprint == fingerprint:
            return False

        expires_at = self._dedupe_expiry_by_key.get(dedupe_key)
        if expires_at is not None and expires_at >= event_time:
            return False

        self._last_state_by_identity[event.identity_key] = fingerprint
        self._dedupe_expiry_by_key[dedupe_key] = event_time + timedelta(
            seconds=self.config.dedupe_window_seconds
        )
        self._buffer.append(event)
        return True

    def flush_due(
        self,
        *,
        now: datetime | None = None,
        force: bool = False,
    ) -> list[SignalEventCandidate]:
        if not self._buffer:
            return []
        now_utc = _as_utc(now or datetime.now(UTC))
        elapsed = (now_utc - self._last_flush_at).total_seconds()
        if (
            not force
            and len(self._buffer) < self.config.max_batch_size
            and elapsed < self.config.flush_interval_seconds
        ):
            return []
        batch = list(self._buffer)
        self._buffer.clear()
        self._last_flush_at = now_utc
        return batch

    def _expire_dedupe_keys(self, now: datetime) -> None:
        expired = [
            key for key, expires_at in self._dedupe_expiry_by_key.items() if expires_at < now
        ]
        for key in expired:
            self._dedupe_expiry_by_key.pop(key, None)


class WorkerHeartbeatBuffer:
    def __init__(
        self,
        config: OpsHeartbeatConfig,
        *,
        initial_now: datetime | None = None,
    ) -> None:
        self.config = config
        self._pending: dict[tuple[str, str], WorkerHeartbeatSample] = {}
        self._last_flush_at = _as_utc(initial_now or datetime.now(UTC))

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def record(self, heartbeat: WorkerHeartbeatSample) -> None:
        key = (heartbeat.lane, heartbeat.worker_name)
        existing = self._pending.get(key)
        if existing is None or _as_utc(heartbeat.heartbeat_at) >= _as_utc(existing.heartbeat_at):
            self._pending[key] = heartbeat

    def flush_due(
        self,
        *,
        now: datetime | None = None,
        force: bool = False,
    ) -> list[WorkerHeartbeatSample]:
        if not self._pending:
            return []
        now_utc = _as_utc(now or datetime.now(UTC))
        elapsed = (now_utc - self._last_flush_at).total_seconds()
        if (
            not force
            and len(self._pending) < self.config.max_batch_size
            and elapsed < self.config.flush_interval_seconds
        ):
            return []
        batch = sorted(self._pending.values(), key=lambda item: (item.lane, item.worker_name))
        self._pending.clear()
        self._last_flush_at = now_utc
        return batch


def build_signal_dedupe_key(event: SignalEventCandidate) -> str:
    closed = _as_utc(event.candle_close_at).isoformat()
    return "|".join(
        [
            event.strategy_slug,
            event.strategy_version,
            event.watchlist_key,
            event.signal_type,
            closed,
        ]
    )


def _signal_state_fingerprint(event: SignalEventCandidate) -> str:
    payload: dict[str, Any] = {
        "signal_type": event.signal_type,
        "state": event.state or event.signal_type,
    }
    return json.dumps(
        sanitize_json_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
