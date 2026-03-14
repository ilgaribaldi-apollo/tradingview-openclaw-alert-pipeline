from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Protocol

from .models import SignalEventCandidate, WatchlistEntry, WorkerHeartbeatSample


class MarketDataPoller(Protocol):
    def fetch_closed_candles(
        self,
        *,
        watchlist: WatchlistEntry,
        limit: int | None = None,
    ) -> Sequence[dict[str, Any]]: ...


class SignalEvaluator(Protocol):
    def evaluate(
        self,
        *,
        watchlist: WatchlistEntry,
        candles: Sequence[dict[str, Any]],
    ) -> Iterable[SignalEventCandidate]: ...


class RuntimeStore(Protocol):
    def write_signal_events(self, events: Sequence[SignalEventCandidate]) -> int: ...

    def write_worker_heartbeats(self, heartbeats: Sequence[WorkerHeartbeatSample]) -> int: ...

    def list_recent_signal_feed(self, *, limit: int = 50) -> Sequence[dict[str, Any]]: ...

    def list_runtime_ops_overview(self, *, limit: int = 50) -> Sequence[dict[str, Any]]: ...
