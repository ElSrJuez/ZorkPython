from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import openai
from foundry_local import FoundryLocalManager

# ---------------------------------------------------------------------------
# Prompt + schema assets shared with narration helpers
# ---------------------------------------------------------------------------

_BASE_DIR = Path(__file__).parent
_CFG_PATH = _BASE_DIR / "config.json"
_RESP_SCHEMA_PATH = _BASE_DIR / "response_schema.json"

CFG = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
RESP_SCHEMA = json.loads(_RESP_SCHEMA_PATH.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Local model bootstrap
# ---------------------------------------------------------------------------

# By using an alias, the most suitable model will be downloaded
# to your end-user's device.
# alias = "gpt-oss-20b-cuda-gpu"
alias = CFG["llm_model_alias"]

# Create a FoundryLocalManager instance. This will start the Foundry
# Local service if it is not already running and load the specified model.
manager = FoundryLocalManager(alias)

# Configure the client to use the local Foundry service
client = openai.OpenAI(
    base_url=manager.endpoint,
    api_key=manager.api_key,  # API key is not required for local usage
)

USER_TMPL: str = CFG["user_prompt_template"]
SYSTEM_PROMPT_TMPL: str = CFG["system_prompt"]
SYSTEM_PROMPT: str = SYSTEM_PROMPT_TMPL.replace(
    "{response_schema}", json.dumps(RESP_SCHEMA, ensure_ascii=False)
)

MAX_LOG_LINES = 40
MAX_TOKENS_CFG = CFG.get("max_tokens", None)

_LOG_DIR = _BASE_DIR / CFG["input_jsonl_path"].rstrip("\\/")
_LOG_DIR.mkdir(parents=True, exist_ok=True)
AI_LOG_PATH = _LOG_DIR / "ai.jsonl"
AI_LOG_PATH.write_text("", encoding="utf-8")

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)
_NARRATION_FIELD_RE = re.compile(
    r"\"narration\"\s*:\s*\"(?P<value>(?:\\.|[^\\\"])*)\"",
    re.IGNORECASE | re.DOTALL,
)

@dataclass(slots=True)
class NarrationContext:
    """Normalized snapshot of a narration planning call (no UI side effects)."""

    messages: List[Dict[str, str]]
    payload: Dict[str, Any]
    narration: str
    raw_content: str


def create_narration_context(
    interactions: Sequence[str],
    *,
    max_log_lines: Optional[int] = None,
) -> NarrationContext:
    """Produce the structured narration payload without streaming to the UI."""

    limit = max_log_lines or MAX_LOG_LINES
    if limit <= 0:
        raise ValueError("max_log_lines must be greater than zero")

    recent_lines = list(interactions[-limit:]) if interactions else []
    excerpt = "\n".join(recent_lines)

    user_content = USER_TMPL.format(game_log=excerpt)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    _append_log({"request": messages})

    kwargs: Dict[str, Any] = {
        "model": manager.get_model_info(alias).id,
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

    resp = client.chat.completions.create(**kwargs)
    msg = resp.choices[0].message
    content = msg.content if isinstance(msg.content, str) else ""

    payload = _find_json_payload(content)
    if payload is None:
        narration_text = _extract_narration_from_text(content)
        payload = {"narration": narration_text or content or ""}

    _append_log({"response": payload})

    narration = str(payload.get("narration", "") or "")

    return NarrationContext(
        messages=messages,
        payload=payload,
        narration=narration,
        raw_content=content,
    )


def _append_log(entry: Dict[str, Any]) -> None:
    with AI_LOG_PATH.open("a", encoding="utf-8") as _log:
        _log.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = _CODE_FENCE_RE.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def _find_json_payload(text: str) -> Optional[Dict[str, Any]]:
    candidate = _strip_code_fence(text)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and start < end:
        snippet = candidate[start : end + 1]
        try:
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
    return None


def _extract_narration_from_text(text: str) -> Optional[str]:
    match = _NARRATION_FIELD_RE.search(text)
    if not match:
        return None
    raw_value = match.group("value")
    try:
        return json.loads(f'"{raw_value}"')
    except json.JSONDecodeError:
        return raw_value.replace("\\\"", "\"").replace("\\n", "\n")
