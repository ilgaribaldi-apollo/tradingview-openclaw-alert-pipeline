from __future__ import annotations

import pandas as pd


def _rsi(series: pd.Series, length: int = 12) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    x = _rsi(df['close'], 12)
    pos = pd.Series(0, index=df.index, dtype='float64')
    pos[x > 70] = 1
    pos[x < 30] = -1
    pos = pos.replace(0, pd.NA).ffill().fillna(0)
    prev = pos.shift(1).fillna(0)
    df['entry'] = (pos == 1) & (prev != 1)
    df['exit'] = (pos == -1) & (prev == 1)
    return df
