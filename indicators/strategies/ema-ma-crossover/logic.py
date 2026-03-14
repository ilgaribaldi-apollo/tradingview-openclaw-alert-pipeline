from __future__ import annotations

import pandas as pd


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    length_ma = 10
    length_ema = 10
    df["xMA"] = df["close"].rolling(length_ma, min_periods=length_ma).mean()
    df["xEMA"] = df["xMA"].ewm(span=length_ema, adjust=False, min_periods=length_ema).mean()
    df["pos"] = 0
    df.loc[df["xEMA"] < df["xMA"], "pos"] = 1
    df.loc[df["xEMA"] > df["xMA"], "pos"] = -1
    df["pos"] = df["pos"].replace(0, pd.NA).ffill().fillna(0)
    prev_pos = df["pos"].shift(1).fillna(0)
    df["entry"] = (df["pos"] == 1) & (prev_pos != 1)
    df["exit"] = (df["pos"] == -1) & (prev_pos == 1)
    return df
