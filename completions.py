"""OpenAI completion utilities.

Adds build_messages(recent_lines) which converts recent game text in to the
schema expected by OpenAI chat completions, using the prompts from config.json.
The existing demo streaming call is preserved at bottom.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Generator, Iterable

from zork_ai import manager, alias, client
from zork_ai_controllers import ask_ai
# -----------------------------------------------------------------------------
# Helper to stream AI response into the right-hand pane (UI passed in)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Prompt config
# -----------------------------------------------------------------------------

_CFG_PATH = Path(__file__).with_name("config.json")
CFG = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
USER_TMPL: str = CFG["user_prompt_template"]
MAX_LOG_LINES = 40  # lines to include from game log
STREAM_ONLY_NARRATION: bool = bool(CFG.get("stream_only_narration", False))
MAX_TOKENS_CFG = CFG.get("max_tokens", None)

# ai.jsonl path and reset per session, using configured log path
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / CFG["input_jsonl_path"].rstrip("\\/")
LOG_DIR.mkdir(parents=True, exist_ok=True)
AI_LOG_PATH = LOG_DIR / "ai.jsonl"
# clear previous messages
AI_LOG_PATH.write_text("", encoding="utf-8")

# Structured Outputs schema
RESP_SCHEMA_PATH = BASE_DIR / "response_schema.json"
RESP_SCHEMA = json.loads(RESP_SCHEMA_PATH.read_text(encoding="utf-8"))

# Inject schema into the system prompt when placeholder is present
SYSTEM_PROMPT_TMPL: str = CFG["system_prompt"]
SYSTEM_PROMPT: str = SYSTEM_PROMPT_TMPL.replace(
    "{response_schema}", json.dumps(RESP_SCHEMA, ensure_ascii=False)
)

def build_messages(recent_lines: List[str]) -> List[Dict[str, str]]:
    """Return list[dict] in OpenAI chat format from recent log lines."""
    excerpt = "\n".join(recent_lines[-MAX_LOG_LINES:])
    user_content = USER_TMPL.format(game_log=excerpt)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

class OpenAICompletionService:
    """Structured output service that streams either the raw JSON or narration only.

    We intentionally call the API in non-streaming mode to obtain a strict
    JSON object following `response_schema.json`, then stream the chosen text
    to the UI in small chunks for a smooth experience.
    """

    def _chunk(self, text: str, size: int = 140) -> Iterable[str]:
        buf: List[str] = []
        count = 0
        for w in text.split():
            wl = len(w) + 1
            if buf and count + wl > size:
                yield " ".join(buf) + " "
                buf.clear()
                count = 0
            buf.append(w)
            count += wl
        if buf:
            yield " ".join(buf)

    def get_stream(self, recent_lines: List[str]):
        messages = build_messages(recent_lines)

        # Log request
        with AI_LOG_PATH.open("a", encoding="utf-8") as _log:
            _log.write(json.dumps({"request": messages}) + "\n")

        kwargs = {
            "model": manager.get_model_info(alias).id,  # type: ignore[attr-defined]
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "zork_ai_reply",
                    "schema": RESP_SCHEMA,
                    "strict": True,
                },
            },
        }
        if isinstance(MAX_TOKENS_CFG, int) and MAX_TOKENS_CFG > 0:
            kwargs["max_tokens"] = MAX_TOKENS_CFG

        resp = client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
        msg = resp.choices[0].message
        content = msg.content if isinstance(msg.content, str) else ""

        try:
            obj = json.loads(content)
        except Exception:
            obj = {"narration": content or ""}

        # Persist response object
        with AI_LOG_PATH.open("a", encoding="utf-8") as _log:
            _log.write(json.dumps({"response": obj}, ensure_ascii=False) + "\n")

        # Decide what to stream
        if STREAM_ONLY_NARRATION:
            to_stream = obj.get("narration", "")
        else:
            # Stream full JSON for debugging visibility
            to_stream = json.dumps(obj, ensure_ascii=False, indent=2)

        for part in self._chunk(to_stream):
            yield part
        return to_stream


def stream_to_ui(ui, recent_lines: List[str]):
    """Generate an AI assistant response and stream it to the UI via controller."""
    # Delegate to the controller to manage UI lifecycle and finalization
    ask_ai(ui, recent_lines, OpenAICompletionService())


