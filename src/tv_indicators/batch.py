from __future__ import annotations

from pathlib import Path
from typing import Any

from .backtest import run_indicator_backtest
from .io import read_yaml
from .paths import METADATA_DIR
from .reporting import append_failed_run


def list_indicator_slugs(statuses: set[str] | None = None) -> list[str]:
    slugs: list[str] = []
    for path in sorted(METADATA_DIR.glob("*.yaml")):
        data = read_yaml(path)
        status = str(data.get("status", ""))
        if statuses and status not in statuses:
            continue
        slugs.append(path.stem)
    return slugs


def run_batch(
    *,
    statuses: set[str] | None = None,
    config_name: str = "default-matrix.yaml",
    exchange: str | None = None,
) -> list[dict[str, Any]]:
    results = []
    for slug in list_indicator_slugs(statuses=statuses):
        try:
            results.append(
                run_indicator_backtest(
                    indicator_slug=slug,
                    config_name=config_name,
                    exchange=exchange,
                )
            )
        except Exception as exc:  # noqa: BLE001
            append_failed_run(slug, str(exc))
            results.append({"indicator_slug": slug, "error": str(exc)})
    return results
