"""OpenAI completion utilities.

Adds build_messages(recent_lines) which converts recent game text in to the
schema expected by OpenAI chat completions, using the prompts from config.json.
The existing demo streaming call is preserved at bottom.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

from zork_ai import manager, alias, client
# -----------------------------------------------------------------------------
# Helper to stream AI response into the right-hand pane (UI passed in)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Prompt config
# -----------------------------------------------------------------------------
_CFG_PATH = Path(__file__).with_name("config.json")
CFG = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
SYSTEM_PROMPT: str = CFG["system_prompt"]
USER_TMPL: str = CFG["user_prompt_template"]
MAX_LOG_LINES = 40  # lines to include from game log


def build_messages(recent_lines: List[str]) -> List[Dict[str, str]]:
    """Return list[dict] in OpenAI chat format from recent log lines."""
    excerpt = "\n".join(recent_lines[-MAX_LOG_LINES:])
    user_content = USER_TMPL.format(game_log=excerpt)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def stream_to_ui(ui, recent_lines: List[str]):
    """Generate an AI assistant response and stream it to the UI pane."""
    messages = build_messages(recent_lines)

    stream = client.chat.completions.create(  # type: ignore[arg-type]
        model=manager.get_model_info(alias).id,  # type: ignore[attr-defined]
        messages=messages,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            ui.write_ai(delta)
