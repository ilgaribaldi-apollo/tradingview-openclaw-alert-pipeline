from __future__ import annotations

import pandas as pd


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    macd_fast = df["close"].ewm(span=12, adjust=False).mean()
    macd_slow = df["close"].ewm(span=26, adjust=False).mean()
    df["macd_line"] = macd_fast - macd_slow
    df["signal_line"] = df["macd_line"].rolling(9, min_periods=9).mean()
    df["pos"] = 0
    df.loc[df["macd_line"] > df["signal_line"], "pos"] = 1
    df.loc[df["macd_line"] < df["signal_line"], "pos"] = -1
    df["pos"] = df["pos"].replace(0, pd.NA).ffill().fillna(0)
    prev_pos = df["pos"].shift(1).fillna(0)
    df["entry"] = (df["pos"] == 1) & (prev_pos != 1)
    df["exit"] = (df["pos"] == -1) & (prev_pos == 1)
    return df
