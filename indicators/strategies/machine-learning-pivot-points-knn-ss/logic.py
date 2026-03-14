from __future__ import annotations

import numpy as np
import pandas as pd


PIVOT_BARS = 10
SLOPE_WINDOW = 20


def _confirmed_pivot_low(series: pd.Series, bars: int = PIVOT_BARS) -> pd.Series:
    out = pd.Series(False, index=series.index)
    for i in range(bars, len(series) - bars):
        window = series.iloc[i - bars : i + bars + 1]
        if series.iloc[i] == window.min():
            out.iloc[i + bars] = True
    return out


def _confirmed_pivot_high(series: pd.Series, bars: int = PIVOT_BARS) -> pd.Series:
    out = pd.Series(False, index=series.index)
    for i in range(bars, len(series) - bars):
        window = series.iloc[i - bars : i + bars + 1]
        if series.iloc[i] == window.max():
            out.iloc[i + bars] = True
    return out


def _rolling_slope(series: pd.Series, window: int = SLOPE_WINDOW) -> pd.Series:
    x = np.arange(window)

    def slope(vals: np.ndarray) -> float:
        if np.isnan(vals).any():
            return np.nan
        return float(np.polyfit(x, vals, 1)[0])

    return series.rolling(window).apply(slope, raw=True)


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pivot_low_confirmed"] = _confirmed_pivot_low(df["low"])
    df["pivot_high_confirmed"] = _confirmed_pivot_high(df["high"])
    df["slope"] = _rolling_slope(df["close"])
    df["entry"] = df["pivot_low_confirmed"] & (df["slope"] > 0)
    df["exit"] = df["pivot_high_confirmed"] & (df["slope"] < 0)
    return df
