-- Sprint 2 runtime foundation
-- Conservative scope: research + runtime observability + paper trading only.
-- Explicitly no live order execution tables or broker credential surfaces.

create extension if not exists pgcrypto;

create type promotion_verdict as enum (
  'reject',
  'keep_researching',
  'paper_trade_candidate',
  'paper_trading',
  'live_candidate',
  'live_shadow',
  'live_enabled'
);

create type strategy_stage as enum (
  'benchmarked',
  'cross_validated',
  'paper_trade_candidate',
  'paper_trading',
  'live_candidate',
  'live_shadow',
  'live_enabled'
);

create type worker_lane as enum ('market_data', 'signals', 'paper', 'ops');
create type worker_status as enum ('idle', 'running', 'degraded', 'failed', 'paused');
create type signal_type as enum ('entry_long', 'exit_long', 'entry_short', 'exit_short', 'flat');
create type signal_source as enum ('local_evaluator', 'tradingview_webhook', 'manual');
create type delivery_status as enum ('queued', 'sent', 'failed', 'skipped');
create type paper_position_status as enum ('open', 'closed', 'cancelled');
create type paper_fill_type as enum ('entry', 'exit', 'adjustment');
create type position_side as enum ('long', 'short', 'flat');
create type watchlist_status as enum ('active', 'paused', 'retired');

create table if not exists strategy_registry (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  source_indicator_slug text not null,
  owner text,
  current_stage strategy_stage not null default 'benchmarked',
  runtime_enabled boolean not null default false,
  paper_enabled boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists strategy_versions (
  id uuid primary key default gen_random_uuid(),
  strategy_registry_id uuid not null references strategy_registry(id) on delete cascade,
  version text not null,
  code_path text not null,
  config_path text,
  config_hash text,
  source_commit text,
  is_active boolean not null default false,
  backtest_evidence jsonb not null default '{}'::jsonb,
  promotion_requirements jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (strategy_registry_id, version)
);

comment on column strategy_versions.backtest_evidence is
  'Store the richer research evidence already emitted by results/config+metrics, including exchange, symbol, timeframe, engine, configured/actual ranges, bar_count, fees/slippage, signal counts, return, drawdown, sharpe, win_rate, trade_count, and notes.';

create table if not exists promotion_decisions (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references strategy_versions(id) on delete cascade,
  verdict promotion_verdict not null,
  stage_from strategy_stage not null,
  stage_to strategy_stage not null,
  rationale text not null,
  reason_codes jsonb not null default '[]'::jsonb,
  strengths jsonb not null default '[]'::jsonb,
  weaknesses jsonb not null default '[]'::jsonb,
  kill_criteria jsonb not null default '[]'::jsonb,
  actor text not null default 'unknown',
  decided_at timestamptz not null default now()
);

create table if not exists symbol_watchlists (
  id uuid primary key default gen_random_uuid(),
  venue text not null,
  symbol text not null,
  timeframe text not null,
  status watchlist_status not null default 'active',
  source text not null default 'manual',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (venue, symbol, timeframe)
);

create table if not exists market_feed_status (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references symbol_watchlists(id) on delete cascade,
  worker_name text not null default 'market_data',
  status worker_status not null default 'idle',
  last_bar_open_time timestamptz,
  last_ingested_at timestamptz,
  lag_seconds integer,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique (watchlist_id, worker_name)
);

create table if not exists runtime_worker_status (
  id uuid primary key default gen_random_uuid(),
  worker_name text not null,
  lane worker_lane not null,
  status worker_status not null,
  heartbeat_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  lag_seconds integer,
  error_summary text,
  metadata jsonb not null default '{}'::jsonb,
  unique (worker_name, lane)
);

create table if not exists signal_events (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references strategy_versions(id) on delete cascade,
  watchlist_id uuid not null references symbol_watchlists(id) on delete restrict,
  signal_type signal_type not null,
  signal_source signal_source not null default 'local_evaluator',
  signal_at timestamptz not null,
  candle_open_at timestamptz,
  candle_close_at timestamptz,
  price numeric(20, 10),
  dedupe_key text not null unique,
  context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists signal_deliveries (
  id uuid primary key default gen_random_uuid(),
  signal_event_id uuid not null references signal_events(id) on delete cascade,
  channel text not null,
  status delivery_status not null default 'queued',
  delivered_at timestamptz,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  unique (signal_event_id, channel)
);

create table if not exists paper_positions (
  id uuid primary key default gen_random_uuid(),
  strategy_version_id uuid not null references strategy_versions(id) on delete restrict,
  opening_signal_event_id uuid references signal_events(id) on delete set null,
  watchlist_id uuid not null references symbol_watchlists(id) on delete restrict,
  side position_side not null,
  status paper_position_status not null default 'open',
  opened_at timestamptz not null,
  closed_at timestamptz,
  entry_price numeric(20, 10) not null,
  exit_price numeric(20, 10),
  quantity numeric(28, 10) not null,
  realized_pnl numeric(28, 10),
  unrealized_pnl numeric(28, 10),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists paper_fills (
  id uuid primary key default gen_random_uuid(),
  paper_position_id uuid not null references paper_positions(id) on delete cascade,
  signal_event_id uuid references signal_events(id) on delete set null,
  fill_type paper_fill_type not null,
  filled_at timestamptz not null,
  price numeric(20, 10) not null,
  quantity numeric(28, 10) not null,
  fees numeric(28, 10) not null default 0,
  notes text,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists idx_strategy_versions_registry_active
  on strategy_versions(strategy_registry_id, is_active);
create index if not exists idx_promotion_decisions_strategy_version_decided_at
  on promotion_decisions(strategy_version_id, decided_at desc);
create index if not exists idx_signal_events_strategy_signal_at
  on signal_events(strategy_version_id, signal_at desc);
create index if not exists idx_signal_events_watchlist_signal_at
  on signal_events(watchlist_id, signal_at desc);
create index if not exists idx_paper_positions_watchlist_status
  on paper_positions(watchlist_id, status);
create index if not exists idx_runtime_worker_status_lane_status
  on runtime_worker_status(lane, status);
create index if not exists idx_market_feed_status_updated_at
  on market_feed_status(updated_at desc);
