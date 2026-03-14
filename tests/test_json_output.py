from __future__ import annotations

import json
from datetime import UTC, datetime

from tv_indicators.io import dumps_json, write_json


def test_dumps_json_normalizes_non_finite_values_to_null():
    payload = {
        "nan": float("nan"),
        "inf": float("inf"),
        "neg_inf": float("-inf"),
        "nested": [1.0, float("nan"), {"ok": 2.5}],
        "timestamp": datetime(2026, 3, 14, 15, 30, tzinfo=UTC),
    }

    raw = dumps_json(payload)
    data = json.loads(raw)

    assert "NaN" not in raw
    assert "Infinity" not in raw
    assert data["nan"] is None
    assert data["inf"] is None
    assert data["neg_inf"] is None
    assert data["nested"][1] is None
    assert data["timestamp"] == "2026-03-14T15:30:00+00:00"


def test_write_json_persists_sanitized_payload(tmp_path):
    path = tmp_path / "metrics.json"

    write_json(
        path,
        {
            "total_return": float("nan"),
            "max_drawdown": 4.2,
            "components": [float("inf"), 1.0],
        },
    )

    written = json.loads(path.read_text(encoding="utf-8"))
    assert written == {
        "components": [None, 1.0],
        "max_drawdown": 4.2,
        "total_return": None,
    }
