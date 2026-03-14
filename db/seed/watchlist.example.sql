-- Example watchlist aligned with the current project defaults.
insert into symbol_watchlists (venue, symbol, timeframe, source)
values
  ('coinbase', 'BTC/USD', '1h', 'project_default'),
  ('coinbase', 'ETH/USD', '1h', 'project_default'),
  ('coinbase', 'SOL/USD', '1h', 'project_default'),
  ('coinbase', 'DOGE/USD', '1h', 'project_default')
on conflict (venue, symbol, timeframe) do nothing;
