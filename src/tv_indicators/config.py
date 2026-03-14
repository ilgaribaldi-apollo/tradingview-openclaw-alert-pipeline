from __future__ import annotations

from pathlib import Path

from .models import TestMatrix
from .paths import BACKTESTS_DIR
from .io import read_yaml


def load_test_matrix(path: str | Path) -> TestMatrix:
    actual_path = Path(path)
    if not actual_path.is_absolute():
        actual_path = BACKTESTS_DIR / "configs" / actual_path
    data = read_yaml(actual_path)
    return TestMatrix(**data)
