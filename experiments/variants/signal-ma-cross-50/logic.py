from __future__ import annotations

import numpy as np
import pandas as pd


def _signal_ma(close: pd.Series, length: int = 50) -> pd.Series:
    target = close.rolling(length, min_periods=length).mean()
    abs_diff = (target - target.shift(1)).abs()
    bar_index = pd.Series(np.arange(len(close)), index=close.index, dtype=float)
    r2 = close.rolling(length, min_periods=length).corr(bar_index).pow(2)
    ma_vals = []
    prev_ma = np.nan
    prev_os = 0.0
    for i in range(len(close)):
        t = target.iloc[i]
        r2_i = r2.iloc[i]
        if np.isnan(t) or np.isnan(r2_i):
            ma_vals.append(np.nan)
            continue
        prev_target = target.iloc[i - 1] if i > 0 else np.nan
        src_prev = close.iloc[i - 1] if i > 0 else np.nan
        if r2_i > 0.5 and not np.isnan(prev_target) and not np.isnan(src_prev):
            prev_os = float(np.sign(src_prev - prev_target))
            base_ma = t if np.isnan(prev_ma) else prev_ma
            current_ma = float(r2_i * t + (1 - r2_i) * base_ma)
        else:
            base_ma = t if np.isnan(prev_ma) else prev_ma
            current_ma = float(base_ma - abs_diff.iloc[i] * prev_os)
        prev_ma = current_ma
        ma_vals.append(current_ma)
    return pd.Series(ma_vals, index=close.index)


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    sig = _signal_ma(df['close'], 50)
    prev_close = df['close'].shift(1)
    prev_sig = sig.shift(1)
    df['entry'] = (prev_close <= prev_sig) & (df['close'] > sig)
    df['exit'] = (prev_close >= prev_sig) & (df['close'] < sig)
    return df.fillna({'entry': False, 'exit': False})
