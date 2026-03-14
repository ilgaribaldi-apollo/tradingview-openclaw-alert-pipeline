# Webhooks

Inbound webhooks are **not active yet**.

This folder exists so a future TradingView adapter can:
- validate payload shape before touching runtime state
- translate alerts into `api/contracts/` objects
- keep webhook ingestion separate from the local Python evaluator path
