from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = ta.ema(df["close"], length=9)
    df["ema_slow"] = ta.ema(df["close"], length=21)

    prev_fast = df["ema_fast"].shift(1)
    prev_slow = df["ema_slow"].shift(1)

    df["entry"] = (prev_fast <= prev_slow) & (df["ema_fast"] > df["ema_slow"])
    df["exit"] = (prev_fast >= prev_slow) & (df["ema_fast"] < df["ema_slow"])
    return df
