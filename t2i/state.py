"""Shared state for the text-to-image companion."""
from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional

_last_ai_payload: Optional[Dict[str, Any]] = None
_turn_index: int = 0
_LOCK = Lock()


def store_ai_payload(payload: Dict[str, Any]) -> None:
    """Persist the latest AI structured response for downstream use."""
    global _last_ai_payload
    with _LOCK:
        _last_ai_payload = payload.copy()


def get_last_ai_payload() -> Optional[Dict[str, Any]]:
    """Return the most recent AI structured response."""
    with _LOCK:
        return None if _last_ai_payload is None else _last_ai_payload.copy()


def next_turn() -> int:
    """Increment and return the deterministic turn index."""
    global _turn_index
    with _LOCK:
        _turn_index += 1
        return _turn_index


def reset_turn_counter() -> None:
    """Reset the turn counter to zero."""
    global _turn_index
    with _LOCK:
        _turn_index = 0
