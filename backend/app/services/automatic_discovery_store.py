
from __future__ import annotations

from threading import RLock
from typing import Any
import time

_STATE_TTL_SECONDS = 3600
_LOCK = RLock()
_STATES: dict[str, dict[str, Any]] = {}


def _cleanup_locked(now: float | None = None) -> None:
    current = time.time() if now is None else now
    expired = [
        dataset_id
        for dataset_id, state in _STATES.items()
        if current - float(state.get("updated_at", current)) > _STATE_TTL_SECONDS
    ]
    for dataset_id in expired:
        _STATES.pop(dataset_id, None)


def get_state(dataset_id: str) -> dict[str, Any] | None:
    with _LOCK:
        _cleanup_locked()
        state = _STATES.get(dataset_id)
        if state is None:
            return None
        state["updated_at"] = time.time()
        return dict(state)


def set_state(dataset_id: str, **values: Any) -> dict[str, Any]:
    with _LOCK:
        _cleanup_locked()
        state = _STATES.setdefault(dataset_id, {})
        state.update(values)
        state["updated_at"] = time.time()
        return dict(state)


def clear_detection(dataset_id: str) -> None:
    with _LOCK:
        state = _STATES.get(dataset_id)
        if state is not None:
            state.pop("detection", None)
            state["updated_at"] = time.time()


def get_detection(dataset_id: str) -> dict[str, Any] | None:
    state = get_state(dataset_id)
    if state is None:
        return None
    detection = state.get("detection")
    return detection if isinstance(detection, dict) else None


def clear_state(dataset_id: str) -> None:
    with _LOCK:
        _STATES.pop(dataset_id, None)
