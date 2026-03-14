# Runtime Adapters

External boundaries belong here, for example:
- TradingView webhook intake
- optional alternate market-data feeds
- future notification channels

Adapters should translate external payloads into internal contracts under `api/contracts/`.
