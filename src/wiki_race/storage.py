from __future__ import annotations

import json
from typing import Any

from .constants import DEFAULT_CONFIG
from .paths import CONFIG_FILE, RESULTS_FILE, TESTS_FILE


def _load_json(path, default):
    try:
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
    except Exception:
        pass
    return default


def _save_json(path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_config() -> dict[str, str]:
    return {**DEFAULT_CONFIG, **_load_json(CONFIG_FILE, {})}


def save_config(config: dict[str, str]) -> None:
    _save_json(CONFIG_FILE, config)


def load_results() -> list[dict[str, Any]]:
    return _load_json(RESULTS_FILE, [])


def append_result(record: dict[str, Any]) -> None:
    results = load_results()
    results.append(record)
    _save_json(RESULTS_FILE, results)


def overwrite_results(records: list[dict[str, Any]]) -> None:
    _save_json(RESULTS_FILE, records)


def clear_results() -> None:
    _save_json(RESULTS_FILE, [])


def load_test_sets() -> list[dict[str, Any]]:
    return _load_json(TESTS_FILE, [])
