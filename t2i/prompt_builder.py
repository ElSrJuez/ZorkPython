"""Prompt construction helpers for the text-to-image companion."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

from zork_config import get_config_value

DEFAULT_STYLE_PRESET = (
    "monochrome ink illustration, retro text-adventure vibe, no UI chrome, no text overlays, avoid anachronisms"
)
NEGATIVE_PROMPT_BASE = (
    "spoilers, puzzle solutions, inventory not visible, photorealism, modern devices, text overlays, disallowed content"
)


@dataclass
class PromptBundle:
    """Represents a fully constructed prompt ready for inference."""

    prompt: str
    negative_prompt: str
    seed: int


def build_prompt_bundle(
    payload: Mapping[str, object],
    *,
    turn_index: int,
    style_preset: str | None = None,
    negative_prompt: str | None = None,
) -> PromptBundle:
    """Create a deterministic prompt bundle from the structured payload."""

    preset = style_preset or get_config_value("image_style_preset", DEFAULT_STYLE_PRESET)
    neg_prompt = negative_prompt or NEGATIVE_PROMPT_BASE

    room_path = str(payload.get("game-room-path", "")).strip()
    location = _extract_location(room_path)
    objects = _extract_bullets(payload.get("game-last-objects", []), max_items=3)
    changes = _extract_bullets(payload.get("game-last-changes", []), max_items=2)
    mood = str(payload.get("game-intent", "")).strip()

    prompt_parts: List[str] = [preset, f"Scene: {location}".strip()]
    if objects:
        prompt_parts.append(f"Objects in view: {', '.join(objects)}")
    if changes:
        prompt_parts.append(f"Recent changes: {', '.join(changes)}")
    if mood:
        prompt_parts.append(f"Mood: {mood}")

    prompt_text = ". ".join(part for part in prompt_parts if part)
    seed = _derive_seed(location, turn_index)
    return PromptBundle(prompt=prompt_text, negative_prompt=neg_prompt, seed=seed)


def _extract_location(room_path: str) -> str:
    if not room_path:
        return "Unknown location"
    for separator in ("->", "→", "|", ","):
        if separator in room_path:
            parts = [part.strip() for part in room_path.split(separator) if part.strip()]
            if parts:
                return parts[-1]
    return room_path.strip()


def _extract_bullets(value: object, *, max_items: int) -> List[str]:
    if not isinstance(value, Sequence):
        return []
    results: List[str] = []
    for raw in value:
        text = str(raw).strip()
        if "—" in text:
            text = text.split("—", 1)[0].strip()
        elif "-" in text:
            text = text.split("-", 1)[0].strip()
        if text:
            results.append(text)
        if len(results) >= max_items:
            break
    return results


def _derive_seed(location: str, turn_index: int) -> int:
    basis = f"{location}|{turn_index}".encode("utf-8")
    digest = hashlib.sha256(basis).hexdigest()
    return int(digest[:8], 16)
