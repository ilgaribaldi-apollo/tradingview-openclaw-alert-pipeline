from __future__ import annotations

import importlib.util
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any

from .io import read_yaml
from .models import ExperimentSpec
from .paths import EXPERIMENT_COMBINATIONS_DIR, EXPERIMENT_VARIANTS_DIR


class ExperimentLoadError(RuntimeError):
    pass


def _experiment_base_dir(kind: str) -> Path:
    if kind == "combination":
        return EXPERIMENT_COMBINATIONS_DIR
    return EXPERIMENT_VARIANTS_DIR


def load_experiment_spec(experiment_slug: str) -> tuple[ExperimentSpec, Path]:
    for kind, base in (("variant", EXPERIMENT_VARIANTS_DIR), ("combination", EXPERIMENT_COMBINATIONS_DIR)):
        config_path = base / experiment_slug / "experiment.yaml"
        if config_path.exists():
            data = read_yaml(config_path)
            if "kind" not in data:
                data["kind"] = kind
            spec = ExperimentSpec(**data)
            return spec, config_path.parent
    raise ExperimentLoadError(f"Experiment not found: {experiment_slug}")


def load_experiment_module(experiment_slug: str) -> tuple[ExperimentSpec, ModuleType]:
    spec, base_dir = load_experiment_spec(experiment_slug)
    module_path = base_dir / spec.logic_path
    if not module_path.exists():
        raise ExperimentLoadError(f"Experiment logic not found: {module_path}")
    import_spec = importlib.util.spec_from_file_location(f"tv_experiment_{experiment_slug}", module_path)
    if import_spec is None or import_spec.loader is None:
        raise ExperimentLoadError(f"Unable to load experiment module for {experiment_slug}")
    module = importlib.util.module_from_spec(import_spec)
    import_spec.loader.exec_module(module)
    return spec, module


def list_experiments(statuses: set[str] | None = None) -> list[ExperimentSpec]:
    items: list[ExperimentSpec] = []
    for base in (EXPERIMENT_VARIANTS_DIR, EXPERIMENT_COMBINATIONS_DIR):
        if not base.exists():
            continue
        for path in sorted(base.glob('*/experiment.yaml')):
            spec = ExperimentSpec(**read_yaml(path))
            if statuses and spec.status not in statuses:
                continue
            items.append(spec)
    return items
