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
    df["xRSI"] = _rsi(df["close"], 12)
    df["pos"] = 0
    df.loc[df["xRSI"] > 70, "pos"] = 1
    df.loc[df["xRSI"] < 30, "pos"] = -1
    df["pos"] = df["pos"].replace(0, pd.NA).ffill().fillna(0)
    prev_pos = df["pos"].shift(1).fillna(0)
    df["entry"] = (df["pos"] == 1) & (prev_pos != 1)
    df["exit"] = (df["pos"] == -1) & (prev_pos == 1)
    return df
