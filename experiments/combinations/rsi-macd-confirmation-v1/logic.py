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
    rsi = _rsi(df['close'], 12)
    rsi_pos = pd.Series(0, index=df.index, dtype='float64')
    rsi_pos[rsi > 70] = 1
    rsi_pos[rsi < 30] = -1
    rsi_pos = rsi_pos.replace(0, pd.NA).ffill().fillna(0)

    macd_line = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
    signal_line = macd_line.rolling(9, min_periods=9).mean()
    macd_pos = pd.Series(0, index=df.index, dtype='float64')
    macd_pos[macd_line > signal_line] = 1
    macd_pos[macd_line < signal_line] = -1
    macd_pos = macd_pos.replace(0, pd.NA).ffill().fillna(0)

    combo_pos = pd.Series(0, index=df.index, dtype='float64')
    combo_pos[(rsi_pos == 1) & (macd_pos == 1)] = 1
    combo_pos[(rsi_pos == -1) | (macd_pos == -1)] = -1
    combo_pos = combo_pos.replace(0, pd.NA).ffill().fillna(0)
    prev = combo_pos.shift(1).fillna(0)
    df['entry'] = (combo_pos == 1) & (prev != 1)
    df['exit'] = (combo_pos == -1) & (prev == 1)
    return df
