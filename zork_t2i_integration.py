"""Glue between the game loop and the text-to-image companion."""
from __future__ import annotations

from typing import Iterable, Optional

from image_companion_gui import ImageCompanionGUI, PromptPreview
from t2i import state as t2i_state
from t2i.prompt_builder import build_prompt_bundle
from zork_logging import system_log

_gui: Optional[ImageCompanionGUI] = None
_enabled: bool = False


def initialize(enable_gui: bool) -> None:
    """Configure the integration and, if requested, start the GUI companion."""
    global _enabled, _gui
    _enabled = enable_gui
    t2i_state.reset_turn_counter()
    if not _enabled:
        if _gui:
            _gui.stop()
            _gui = None
        system_log("Image companion disabled via configuration.")
        return

    if _gui is None:
        try:
            _gui = ImageCompanionGUI()
            _gui.start()
        except RuntimeError as exc:
            system_log(f"Image companion GUI failed to start: {exc}")
            _enabled = False
            _gui = None
            return
    _gui.set_status("Awaiting narrator response…")
    system_log("Image companion GUI initialized.")


def handle_scene_ready(_transcript_window: Iterable[str]) -> None:
    """Build the prompt for the latest scene and update the GUI."""
    if not _enabled or _gui is None:
        return

    payload = t2i_state.get_last_ai_payload()
    if not payload:
        _gui.set_status("Waiting for structured AI response…")
        return

    turn_index = t2i_state.next_turn()
    bundle = build_prompt_bundle(payload, turn_index=turn_index)
    _gui.show_prompt(
        PromptPreview(
            prompt=bundle.prompt,
            negative_prompt=bundle.negative_prompt,
            seed=bundle.seed,
        )
    )
    _gui.set_status("Prompt ready – image generation pending model selection.")
    system_log(f"Prepared image prompt seed={bundle.seed}")


def is_enabled() -> bool:
    return _enabled
