from __future__ import annotations

from typing import Any

import pandas as pd

from .io import read_yaml
from .paths import BACKTESTS_DIR


def load_filter_pack(name: str) -> dict[str, Any]:
    return read_yaml(BACKTESTS_DIR / 'configs' / 'filters' / f'{name}.yaml')


def load_exit_pack(name: str) -> dict[str, Any]:
    return read_yaml(BACKTESTS_DIR / 'configs' / 'exits' / f'{name}.yaml')


def apply_filter_packs(df: pd.DataFrame, entries: pd.Series, filter_names: list[str]) -> pd.Series:
    filtered = entries.copy().fillna(False).astype(bool)
    for name in filter_names:
        config = load_filter_pack(name)
        kind = config.get('kind')
        if kind == 'above_ema':
            length = int(config.get('length', 200))
            ema = df['close'].ewm(span=length, adjust=False).mean()
            filtered = filtered & (df['close'] > ema)
        elif kind == 'min_atr_percent':
            length = int(config.get('length', 14))
            threshold = float(config.get('threshold', 0.01))
            tr = pd.concat([
                df['high'] - df['low'],
                (df['high'] - df['close'].shift(1)).abs(),
                (df['low'] - df['close'].shift(1)).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(length, min_periods=length).mean()
            atr_pct = atr / df['close']
            filtered = filtered & (atr_pct >= threshold)
    return filtered.fillna(False)


def apply_exit_packs(df: pd.DataFrame, exits: pd.Series, exit_names: list[str]) -> pd.Series:
    adjusted = exits.copy().fillna(False).astype(bool)
    for name in exit_names:
        config = load_exit_pack(name)
        kind = config.get('kind')
        if kind == 'time_stop_bars':
            # Placeholder for future stateful runner support. Kept documented/configurable now.
            continue
        if kind == 'opposite_signal':
            continue
    return adjusted.fillna(False)
