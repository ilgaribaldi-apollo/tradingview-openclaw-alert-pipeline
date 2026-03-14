from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .interfaces import RuntimeStore


@dataclass(slots=True)
class RuntimeSignalFeedRow:
    id: str
    signal_at: Any
    strategy_slug: str
    strategy_title: str | None
    venue: str
    symbol: str
    timeframe: str
    signal_type: str
    signal_source: str
    price: float | None
    dedupe_key: str
    context: dict[str, Any]
    strategy_version: str


@dataclass(slots=True)
class RuntimeOpsOverviewRow:
    worker_name: str
    lane: str
    status: str
    heartbeat_at: Any
    lag_seconds: int | None
    error_summary: str | None
    tracked_feeds: int


class RuntimeReadModelQueries:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    def recent_signals(self, *, limit: int = 50) -> list[RuntimeSignalFeedRow]:
        rows = self.store.list_recent_signal_feed(limit=limit)
        return [
            RuntimeSignalFeedRow(
                id=str(row["id"]),
                signal_at=row["signal_at"],
                strategy_slug=str(row["strategy_slug"]),
                strategy_title=_optional_text(row.get("strategy_title")),
                venue=str(row["venue"]),
                symbol=str(row["symbol"]),
                timeframe=str(row["timeframe"]),
                signal_type=str(row["signal_type"]),
                signal_source=str(row["signal_source"]),
                price=_optional_float(row.get("price")),
                dedupe_key=str(row["dedupe_key"]),
                context=dict(row.get("context") or {}),
                strategy_version=str(row["strategy_version"]),
            )
            for row in rows
        ]

    def ops_overview(self, *, limit: int = 50) -> list[RuntimeOpsOverviewRow]:
        rows = self.store.list_runtime_ops_overview(limit=limit)
        return [
            RuntimeOpsOverviewRow(
                worker_name=str(row["worker_name"]),
                lane=str(row["lane"]),
                status=str(row["status"]),
                heartbeat_at=row["heartbeat_at"],
                lag_seconds=_optional_int(row.get("lag_seconds")),
                error_summary=_optional_text(row.get("error_summary")),
                tracked_feeds=int(row.get("tracked_feeds") or 0),
            )
            for row in rows
        ]


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
