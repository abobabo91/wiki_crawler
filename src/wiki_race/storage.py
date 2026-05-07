from __future__ import annotations

import json
import os
from typing import Any

from .constants import DEFAULT_CONFIG
from .paths import CONFIG_FILE, RESULTS_FILE, TESTS_FILE


# ── JSON helpers (local fallback) ──

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


# ── Firestore (optional, enabled when GOOGLE_CLOUD_PROJECT is set) ──

_db = None
_FIRESTORE_DB = os.environ.get("FIRESTORE_DATABASE", "wikirace")
_COLLECTION = "results"


def _get_db():
    global _db
    if _db is None:
        try:
            from google.cloud import firestore
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            if not project:
                return None
            _db = firestore.Client(project=project, database=_FIRESTORE_DB)
        except Exception:
            return None
    return _db


def _firestore_load_results() -> list[dict[str, Any]] | None:
    db = _get_db()
    if not db:
        return None
    try:
        docs = db.collection(_COLLECTION).order_by("timestamp").stream()
        return [doc.to_dict() for doc in docs]
    except Exception:
        return None


def _firestore_append(record: dict[str, Any]) -> None:
    db = _get_db()
    if not db:
        return
    try:
        db.collection(_COLLECTION).add(record)
    except Exception:
        pass


def _firestore_clear() -> None:
    db = _get_db()
    if not db:
        return
    try:
        docs = db.collection(_COLLECTION).stream()
        for doc in docs:
            doc.reference.delete()
    except Exception:
        pass


# ── Public API (Firestore-first, JSON fallback) ──

def load_config() -> dict[str, str]:
    return {**DEFAULT_CONFIG, **_load_json(CONFIG_FILE, {})}


def save_config(config: dict[str, str]) -> None:
    _save_json(CONFIG_FILE, config)


def load_results() -> list[dict[str, Any]]:
    fs = _firestore_load_results()
    if fs is not None:
        return fs
    return _load_json(RESULTS_FILE, [])


def append_result(record: dict[str, Any]) -> None:
    _firestore_append(record)
    # Also save to local JSON as backup
    results = _load_json(RESULTS_FILE, [])
    results.append(record)
    _save_json(RESULTS_FILE, results)


def overwrite_results(records: list[dict[str, Any]]) -> None:
    _save_json(RESULTS_FILE, records)


def clear_results() -> None:
    _firestore_clear()
    _save_json(RESULTS_FILE, [])


def load_test_sets() -> list[dict[str, Any]]:
    return _load_json(TESTS_FILE, [])
