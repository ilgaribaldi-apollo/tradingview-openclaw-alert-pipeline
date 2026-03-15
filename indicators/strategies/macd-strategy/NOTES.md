# MACD Strategy

## Source status
The TradingView skill confirmed the target public script identity (`MACD Strategy` by HPotter) from search results.

## Important caveat
During this session, TradingView's Pine editor stayed stuck on the previously opened RSI script, so the exact raw Pine body could not be cleanly extracted from the editor pane.

## Working interpretation
This wrapper uses the canonical MACD crossover state logic:
- MACD line = EMA(12) - EMA(26)
- signal line = SMA(MACD, 9)
- long state when MACD > signal
- exit state when MACD < signal

Use this as a practical workflow/backtest artifact, not a courtroom-grade source capture.
