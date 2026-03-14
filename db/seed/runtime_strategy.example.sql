-- Example development bootstrap for the first local signal runner.
-- Keep this explicit and temporary until the promotion lane owns strategy registry writes.

with upsert_registry as (
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
  values (
    'strategy-rsi',
    'Strategy RSI',
    'strategy-rsi',
    'apollo',
    'paper_trade_candidate',
    true,
    false,
    jsonb_build_object('bootstrap', 'runtime_strategy.example.sql')
  )
  on conflict (slug)
  do update set
    title = excluded.title,
    source_indicator_slug = excluded.source_indicator_slug,
    current_stage = excluded.current_stage,
    runtime_enabled = excluded.runtime_enabled,
    updated_at = now()
  returning id
)
insert into strategy_versions (
  strategy_registry_id,
  version,
  code_path,
  is_active,
  backtest_evidence,
  promotion_requirements
)
select
  id,
  'local-v1',
  'indicators/strategies/strategy-rsi/logic.py',
  true,
  '{}'::jsonb,
  jsonb_build_object('note', 'development bootstrap until promotion workflow is wired')
from upsert_registry
on conflict (strategy_registry_id, version)
do update set
  code_path = excluded.code_path,
  is_active = excluded.is_active,
  promotion_requirements = excluded.promotion_requirements;
