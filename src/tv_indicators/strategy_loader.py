from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from .paths import STRATEGIES_DIR


class StrategyLoadError(RuntimeError):
    pass


def load_strategy_module(slug: str) -> ModuleType:
    module_path = STRATEGIES_DIR / slug / "logic.py"
    if not module_path.exists():
        raise StrategyLoadError(f"Strategy logic not found: {module_path}")
    spec = importlib.util.spec_from_file_location(f"tv_indicator_{slug}", module_path)
    if spec is None or spec.loader is None:
        raise StrategyLoadError(f"Unable to load strategy module for {slug}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
