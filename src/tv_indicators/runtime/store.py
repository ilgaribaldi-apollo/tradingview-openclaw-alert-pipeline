from __future__ import annotations

import json
import os
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from ..io import sanitize_json_value
from .models import RuntimeDatabaseConfig, SignalEventCandidate, WorkerHeartbeatSample
from .promotion import StrategyPromotionPayload
from .services import build_signal_dedupe_key


class RuntimeStoreError(RuntimeError):
    pass


class PostgresRuntimeStore:
    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory
        self._watchlist_id_cache: dict[tuple[str, str, str], str] = {}
        self._strategy_version_id_cache: dict[tuple[str, str], str] = {}

    @classmethod
    def from_database_config(cls, database: RuntimeDatabaseConfig) -> "PostgresRuntimeStore":
        database_url = os.getenv(database.url_env)
        if not database_url:
            raise RuntimeStoreError(
                f"Environment variable {database.url_env} is required "
                "for Neon/Postgres runtime writes"
            )

        def _connect() -> Any:
            try:
                import psycopg
            except ImportError as exc:  # pragma: no cover - runtime-only import path
                raise RuntimeStoreError(
                    "psycopg is required for Neon/Postgres runtime writes; "
                    "install project dependencies first"
                ) from exc
            return psycopg.connect(database_url)

        return cls(_connect)

    def write_signal_events(self, events: Sequence[SignalEventCandidate]) -> int:
        items = list(events)
        if not items:
            return 0
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                rows: list[tuple[Any, ...]] = []
                for event in items:
                    watchlist_id = self._resolve_watchlist_id(
                        cursor,
                        event.venue,
                        event.symbol,
                        event.timeframe,
                    )
                    strategy_version_id = self._resolve_strategy_version_id(
                        cursor,
                        strategy_slug=event.strategy_slug,
                        strategy_version=event.strategy_version,
                    )
                    rows.append(
                        (
                            strategy_version_id,
                            watchlist_id,
                            event.signal_type,
                            event.signal_source,
                            _normalize_timestamp(event.signal_at),
                            _normalize_timestamp(event.candle_open_at),
                            _normalize_timestamp(event.candle_close_at),
                            event.price,
                            build_signal_dedupe_key(event),
                            _encode_json(event.context),
                        )
                    )
                sql = _values_sql(
                    """
                    insert into signal_events (
                      strategy_version_id,
                      watchlist_id,
                      signal_type,
                      signal_source,
                      signal_at,
                      candle_open_at,
                      candle_close_at,
                      price,
                      dedupe_key,
                      context
                    )
                    values {values}
                    on conflict (dedupe_key) do nothing
                    returning dedupe_key
                    """,
                    column_count=10,
                    row_count=len(rows),
                )
                flat_params = [value for row in rows for value in row]
                cursor.execute(sql, flat_params)
                inserted = len(cursor.fetchall())
            connection.commit()
            return inserted
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def write_worker_heartbeats(self, heartbeats: Sequence[WorkerHeartbeatSample]) -> int:
        items = list(heartbeats)
        if not items:
            return 0
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                rows = [
                    (
                        sample.worker_name,
                        sample.lane,
                        sample.status,
                        _normalize_timestamp(sample.heartbeat_at),
                        _normalize_timestamp(sample.heartbeat_at),
                        sample.lag_seconds,
                        sample.error_summary,
                        _encode_json(sample.stats),
                    )
                    for sample in items
                ]
                sql = _values_sql(
                    """
                    insert into runtime_worker_status (
                      worker_name,
                      lane,
                      status,
                      heartbeat_at,
                      started_at,
                      lag_seconds,
                      error_summary,
                      metadata
                    )
                    values {values}
                    on conflict (worker_name, lane)
                    do update set
                      status = excluded.status,
                      heartbeat_at = excluded.heartbeat_at,
                      started_at = coalesce(runtime_worker_status.started_at, excluded.started_at),
                      lag_seconds = excluded.lag_seconds,
                      error_summary = excluded.error_summary,
                      metadata = excluded.metadata,
                      finished_at = null
                    returning worker_name, lane
                    """,
                    column_count=8,
                    row_count=len(rows),
                )
                flat_params = [value for row in rows for value in row]
                cursor.execute(sql, flat_params)
                written = len(cursor.fetchall())
            connection.commit()
            return written
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_recent_signal_feed(self, *, limit: int = 50) -> list[dict[str, Any]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      id,
                      signal_at,
                      strategy_slug,
                      strategy_title,
                      venue,
                      symbol,
                      timeframe,
                      signal_type,
                      signal_source,
                      price,
                      dedupe_key,
                      context,
                      strategy_version
                    from runtime_signal_feed
                    order by signal_at desc
                    limit %s
                    """,
                    [limit],
                )
                rows = cursor.fetchall()
                return _rows_to_dicts(cursor, rows)
        finally:
            connection.close()

    def list_runtime_ops_overview(self, *, limit: int = 50) -> list[dict[str, Any]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      worker_name,
                      lane,
                      status,
                      heartbeat_at,
                      lag_seconds,
                      error_summary,
                      tracked_feeds
                    from runtime_ops_overview
                    order by lane, worker_name
                    limit %s
                    """,
                    [limit],
                )
                rows = cursor.fetchall()
                return _rows_to_dicts(cursor, rows)
        finally:
            connection.close()

    def list_runtime_strategy_bindings(self, *, limit: int = 20) -> list[dict[str, Any]]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      sr.slug,
                      sr.title,
                      sr.current_stage,
                      sr.runtime_enabled,
                      sr.paper_enabled,
                      sv.version,
                      sv.code_path,
                      sv.config_path,
                      sv.config_hash,
                      sv.backtest_evidence,
                      sv.promotion_requirements,
                      pd.verdict as latest_verdict,
                      pd.rationale as latest_rationale,
                      pd.decided_at
                    from strategy_registry sr
                    join strategy_versions sv
                      on sv.strategy_registry_id = sr.id
                     and sv.is_active = true
                    join lateral (
                      select verdict, rationale, decided_at
                      from promotion_decisions
                      where strategy_version_id = sv.id
                      order by decided_at desc
                      limit 1
                    ) pd on true
                    where sr.runtime_enabled = true
                      and sr.current_stage in (
                        'paper_trade_candidate',
                        'paper_trading',
                        'live_candidate',
                        'live_shadow',
                        'live_enabled'
                      )
                    order by pd.decided_at desc, sr.slug asc
                    limit %s
                    """,
                    [limit],
                )
                rows = cursor.fetchall()
                return _rows_to_dicts(cursor, rows)
        finally:
            connection.close()

    def apply_strategy_promotion(self, payload: StrategyPromotionPayload) -> dict[str, Any]:
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select id, current_stage
                    from strategy_registry
                    where slug = %s
                    limit 1
                    """,
                    [payload.slug],
                )
                existing = cursor.fetchone()
                stage_from = "benchmarked"
                if existing:
                    if isinstance(existing, dict):
                        stage_from = str(existing.get("current_stage") or stage_from)
                    else:
                        stage_from = str(existing[1] or stage_from)

                cursor.execute(
                    """
                    insert into strategy_registry (
                      slug,
                      title,
                      source_indicator_slug,
                      owner,
                      current_stage,
                      runtime_enabled,
                      paper_enabled,
                      metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    on conflict (slug)
                    do update set
                      title = excluded.title,
                      source_indicator_slug = excluded.source_indicator_slug,
                      owner = excluded.owner,
                      current_stage = excluded.current_stage,
                      runtime_enabled = excluded.runtime_enabled,
                      paper_enabled = excluded.paper_enabled,
                      metadata = excluded.metadata,
                      updated_at = now()
                    returning id
                    """,
                    [
                        payload.slug,
                        payload.title,
                        payload.source_indicator_slug,
                        payload.owner,
                        payload.stage_to,
                        payload.runtime_enabled,
                        payload.paper_enabled,
                        _encode_json(payload.registry_metadata),
                    ],
                )
                registry_row = cursor.fetchone()
                if not registry_row:
                    raise RuntimeStoreError(
                        f"Unable to upsert strategy registry row for {payload.slug}"
                    )
                registry_id = registry_row[0] if not isinstance(registry_row, dict) else registry_row["id"]

                cursor.execute(
                    """
                    update strategy_versions
                    set is_active = false
                    where strategy_registry_id = %s
                      and version <> %s
                    """,
                    [registry_id, payload.version],
                )
                cursor.execute(
                    """
                    insert into strategy_versions (
                      strategy_registry_id,
                      version,
                      code_path,
                      config_path,
                      config_hash,
                      source_commit,
                      is_active,
                      backtest_evidence,
                      promotion_requirements
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    on conflict (strategy_registry_id, version)
                    do update set
                      code_path = excluded.code_path,
                      config_path = excluded.config_path,
                      config_hash = excluded.config_hash,
                      source_commit = excluded.source_commit,
                      is_active = excluded.is_active,
                      backtest_evidence = excluded.backtest_evidence,
                      promotion_requirements = excluded.promotion_requirements
                    returning id
                    """,
                    [
                        registry_id,
                        payload.version,
                        payload.code_path,
                        payload.config_path,
                        payload.config_hash,
                        payload.source_commit,
                        True,
                        _encode_json(payload.backtest_evidence),
                        _encode_json(payload.promotion_requirements),
                    ],
                )
                version_row = cursor.fetchone()
                if not version_row:
                    raise RuntimeStoreError(
                        "Unable to upsert strategy version row for "
                        f"{payload.slug}@{payload.version}"
                    )
                strategy_version_id = (
                    version_row[0] if not isinstance(version_row, dict) else version_row["id"]
                )

                cursor.execute(
                    """
                    insert into promotion_decisions (
                      strategy_version_id,
                      verdict,
                      stage_from,
                      stage_to,
                      rationale,
                      reason_codes,
                      strengths,
                      weaknesses,
                      kill_criteria,
                      actor
                    )
                    values (
                      %s,
                      %s,
                      %s,
                      %s,
                      %s,
                      %s::jsonb,
                      %s::jsonb,
                      %s::jsonb,
                      %s::jsonb,
                      %s
                    )
                    returning id, decided_at
                    """,
                    [
                        strategy_version_id,
                        payload.verdict,
                        stage_from,
                        payload.stage_to,
                        payload.rationale,
                        _encode_json(payload.reason_codes),
                        _encode_json(payload.strengths),
                        _encode_json(payload.weaknesses),
                        _encode_json(payload.kill_criteria),
                        payload.actor,
                    ],
                )
                decision_row = cursor.fetchone()
                if not decision_row:
                    raise RuntimeStoreError(
                        "Unable to insert promotion decision for "
                        f"{payload.slug}@{payload.version}"
                    )
            connection.commit()
            return {
                "slug": payload.slug,
                "version": payload.version,
                "stage_from": stage_from,
                "stage_to": payload.stage_to,
                "runtime_enabled": payload.runtime_enabled,
                "paper_enabled": payload.paper_enabled,
                "verdict": payload.verdict,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _resolve_watchlist_id(self, cursor: Any, venue: str, symbol: str, timeframe: str) -> str:
        cache_key = (venue, symbol, timeframe)
        cached = self._watchlist_id_cache.get(cache_key)
        if cached is not None:
            return cached
        cursor.execute(
            """
            insert into symbol_watchlists (venue, symbol, timeframe, source)
            values (%s, %s, %s, %s)
            on conflict (venue, symbol, timeframe)
            do update set source = symbol_watchlists.source
            returning id
            """,
            [venue, symbol, timeframe, "runtime_worker"],
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeStoreError(
                f"Unable to resolve watchlist row for {venue} {symbol} {timeframe}"
            )
        watchlist_id = row[0] if not isinstance(row, dict) else row["id"]
        self._watchlist_id_cache[cache_key] = watchlist_id
        return watchlist_id

    def _resolve_strategy_version_id(
        self,
        cursor: Any,
        *,
        strategy_slug: str,
        strategy_version: str,
    ) -> str:
        cache_key = (strategy_slug, strategy_version)
        cached = self._strategy_version_id_cache.get(cache_key)
        if cached is not None:
            return cached
        cursor.execute(
            """
            select sv.id
            from strategy_versions sv
            join strategy_registry sr on sr.id = sv.strategy_registry_id
            where sr.slug = %s
              and sv.version = %s
            order by sv.is_active desc, sv.created_at desc
            limit 1
            """,
            [strategy_slug, strategy_version],
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeStoreError(
                "Strategy version row not found for "
                f"{strategy_slug}@{strategy_version}. "
                "Seed or promote the strategy before running signals."
            )
        strategy_version_id = row[0] if not isinstance(row, dict) else row["id"]
        self._strategy_version_id_cache[cache_key] = strategy_version_id
        return strategy_version_id


def _values_sql(template: str, *, column_count: int, row_count: int) -> str:
    placeholders = "(" + ", ".join(["%s"] * column_count) + ")"
    values = ", ".join([placeholders] * row_count)
    return "\n".join(line.rstrip() for line in template.strip().splitlines()).format(values=values)


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _encode_json(payload: Any) -> str:
    return json.dumps(
        sanitize_json_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _rows_to_dicts(cursor: Any, rows: Sequence[Any]) -> list[dict[str, Any]]:
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return [dict(row) for row in rows]
    description = getattr(cursor, "description", None) or []
    columns = [getattr(item, "name", None) or item[0] for item in description]
    return [dict(zip(columns, row, strict=False)) for row in rows]
