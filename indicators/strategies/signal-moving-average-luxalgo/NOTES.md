# Signal Moving Average [LuxAlgo]

## Source status
This script was extracted from a fresh TradingView tab using the hardened exact-row + exact-code-icon workflow.

## Translation note
The original indicator does not define entries/exits. The Python wrapper preserves the adaptive Signal MA construction and then defines a practical wrapper:
- enter when close crosses above the Signal MA
- exit when close crosses below the Signal MA

## Why this one matters
This is a more interesting modern indicator than the earlier HPotter baselines while still being concrete enough to translate honestly.
