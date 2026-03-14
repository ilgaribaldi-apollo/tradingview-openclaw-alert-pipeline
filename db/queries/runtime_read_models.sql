-- Example read models for the future frontend/runtime boundary.
-- Keep dashboard reads aggregated/read-model-friendly instead of issuing chatty row-by-row queries.

create or replace view runtime_signal_feed as
select
  se.id,
  se.signal_at,
  sr.slug as strategy_slug,
  sr.title as strategy_title,
  sw.venue,
  sw.symbol,
  sw.timeframe,
  se.signal_type,
  se.signal_source,
  se.price,
  se.dedupe_key,
  se.context,
  sv.version as strategy_version
from signal_events se
join strategy_versions sv on sv.id = se.strategy_version_id
join strategy_registry sr on sr.id = sv.strategy_registry_id
join symbol_watchlists sw on sw.id = se.watchlist_id
order by se.signal_at desc;

create or replace view runtime_signal_state_change_rollup as
select
  sw.venue,
  sw.symbol,
  sw.timeframe,
  sr.slug as strategy_slug,
  date_trunc('hour', se.signal_at) as bucket_hour,
  count(*) as event_count,
  max(se.signal_at) as latest_signal_at
from signal_events se
join strategy_versions sv on sv.id = se.strategy_version_id
join strategy_registry sr on sr.id = sv.strategy_registry_id
join symbol_watchlists sw on sw.id = se.watchlist_id
group by sw.venue, sw.symbol, sw.timeframe, sr.slug, date_trunc('hour', se.signal_at)
order by bucket_hour desc, sr.slug, sw.symbol, sw.timeframe;

create or replace view runtime_ops_overview as
select
  rws.worker_name,
  rws.lane,
  rws.status,
  rws.heartbeat_at,
  rws.lag_seconds,
  rws.error_summary,
  coalesce(count(distinct mfs.id), 0) as tracked_feeds
from runtime_worker_status rws
left join market_feed_status mfs
  on mfs.worker_name = rws.worker_name
group by rws.worker_name, rws.lane, rws.status, rws.heartbeat_at, rws.lag_seconds, rws.error_summary
order by rws.lane, rws.worker_name;

create or replace view runtime_worker_heartbeat_rollup as
select
  lane,
  worker_name,
  max(heartbeat_at) as latest_heartbeat_at,
  max(lag_seconds) as max_reported_lag_seconds,
  count(*) as heartbeat_rows
from runtime_worker_status
group by lane, worker_name
order by lane, worker_name;

create or replace view open_paper_positions as
select
  pp.id,
  sr.slug as strategy_slug,
  sv.version as strategy_version,
  sw.venue,
  sw.symbol,
  sw.timeframe,
  pp.side,
  pp.status,
  pp.opened_at,
  pp.entry_price,
  pp.quantity,
  pp.realized_pnl,
  pp.unrealized_pnl
from paper_positions pp
join strategy_versions sv on sv.id = pp.strategy_version_id
join strategy_registry sr on sr.id = sv.strategy_registry_id
join symbol_watchlists sw on sw.id = pp.watchlist_id
where pp.status = 'open'
order by pp.opened_at desc;
