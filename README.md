# Zork with AI Gaming Pal

A modern Python playground that fuses the beloved Infocom classic **Zork I** with a live AI companion. Relive the Great Underground Empire while an LLM provides concise, structured insights and narration – all inside a snappy Rich TUI.

---

## 📚 Table of Contents
1. [Features](#features)
2. [Getting Started](#getting-started)
3. [Playing the Game](#playing-the-game)
4. [Architecture & Configuration](#architecture--configuration)
5. [Credits & License](#credits--license)

---

## Features
| Category | Highlights |
|---|---|
| **Authentic Zork Gameplay** | Complete port of Zork I: all rooms, puzzles, treasures, troll, thief, etc. (see `zork_expanded.py`). |
| **AI Gaming Pal** | OpenAI-compatible model (local or cloud) produces structured JSON with: `game-intent`, `game-meta-intent`, `hidden-next-command`, `hidden-next-command-confidence`, and `narration`. |
| **Rich Two-Pane UI** | Left = original game transcript. Right = AI narrator streaming in real time with colour-alternating blocks (`zork_ui.py`). |
| **Structured-Output Pipeline** | `completions.py` injects `response_schema.json` into the prompt, requests strict JSON, logs every turn, and streams narration (or full JSON for debugging). |
| **Config Toggles** | `config.json` controls model prompt, token limits, and `stream_only_narration` switch. |
| **Text-to-Image (T2I) Companion (alpha)** | `--image-companion` flag boots a Tkinter preview window that shows deterministic prompts/seed info while we finish model selection. |


---

## Getting Started

```bash
# 1. Clone
$ git clone https://github.com/yourusername/ZorkPython.git
$ cd ZorkPython

# 2. Install dependencies (Python 3.9+ recommended)
$ pip install -r requirements.txt

# 3. Launch
$ python zork_expanded.py

# 4. Optional GUI Companion (prompts only)
$ python zork_expanded.py --image-companion
```
The Rich interface appears; add `--image-companion` to preview prompt text while we finalize the image backend.


---

## Playing the Game

### Basic Parser Commands
* Movement: `n`/`s`/`e`/`w`, `u`/`d`, `in`, `out` …
* Interaction: `take lamp`, `open door`, `examine mailbox`, `put egg in basket` …
* Utility: `look`, `inventory`, `save`, `restore`, `score`, `quit`.

### AI Companion
* By default **full JSON** is streamed so you can see each field for debugging.
* Set `"stream_only_narration": true` in `config.json` to see just the narration.
* The AI never spoils puzzles; it offers concise hints in the structured fields.

### Tips
1. Map the underground – mazes get tricky.
2. Watch lamp battery life (≈ 330 turns).
3. Save before risky actions.
4. The thief is… opportunistic.

---

## Architecture & Configuration
```
├─ completions.py          # Builds prompts, injects schema, parses LLM JSON
├─ zork_ai_controllers.py  # Orchestrates UI ↔︎ completion service
├─ zork_ui.py              # Rich TUI (game left, AI right)
├─ zork_io.py              # Canonical entry/exit points for printing & input; hooks for AI calls
├─ response_schema.json    # Strict schema enforced on every AI reply
├─ config.json             # System prompt template & runtime flags
└─ log/ai.jsonl            # Every request/response for analysis
```
Key `config.json` fields:

| Field | Purpose |
|-------|---------|
| `system_prompt` | Contains `{response_schema}` placeholder replaced at runtime. |
| `user_prompt_template` | Wraps last N game lines into the user message. |
| `stream_only_narration` | Toggle between full JSON or just narration streaming. |
| `max_tokens` | Optional limit for LLM response length. |
| `enable_image_companion` | Default opt-in flag for the Tkinter prompt preview window. |
| `image_style_preset` | Default art-direction seed used by the prompt builder. |


---

## Bugs and Bugfixes

1. **Eliminate prompt flicker** – optimise Rich `Live` updates.
2. **Filter banner noise** – exclude Zork’s welcome/header lines from LLM prompts.
3. ~~**JSON/Narration Not workging** - AI output is only supposed to display the narration field and hide all others~~ **(Fixed)** – `completions.py` now strips fences/malformed JSON, extracts only the `narration` value when `stream_only_narration` is true, and prevents other fields from reaching the Rich pane.


---

## TODO

1. **Command skip-list** – maintain commands that shouldn’t trigger AI calls (e.g. `save`, `restore`, `quit`).
2. **Second-stage narration** – feed the first-instance structured JSON so that the narration is an experience enhancing second-shot narration.
3. **Inventory helper** – AI suggests useful items or combos based on current state.
4. **Emergency auto-rescue** – when confidence is high, AI may issue an occasional lifesaving command on behalf of the player.
5. **Voice Narration** – Implement TTS (Piper, other) narration and optionally hiding the AI Box.
6. **Text-to-Image hooks (non-blocking)** – Add minimal image display hooks to `zork_ui` and `zork_io` (e.g., `ui.show_image(path|image)`) so a T2I service can render scene art from structured outputs without changing core flow.
7. **Leverage existing entry/exit points** – Use `zork_print`, `collect_printed_messages`, `INTERACTIONS`, and `stream_to_ui` as canonical integration points; avoid reinventing I/O.
8. **Keep GUI minimal** – Good-looking, but not the main objective; image panel should be optional, cache-backed, and non-blocking.

---

## Credits & License

*Original Zork gameplay and text © Infocom / Activision.*

This project is a **GitHub fork of** [`haxorthematrix/ZorkPython`](https://github.com/haxorthematrix/ZorkPython) ― a faithful Python port of Zork I.  The upstream work provided the core game engine, data files, and an extensive original README detailing rooms, puzzles, and mechanics.  All subsequent AI-enhanced features, Rich UI, and structured-output tooling were added in this fork.

Additional acknowledgements:
* **haxorthematrix** – Original Python port maintainer.
* **Infocom team** – Tim Anderson, Marc Blank, Bruce Daniels, Dave Lebling.
* **OpenAI / Foundry Local** – LLM backend powering the AI Gaming Pal.

Code in this repository is MIT-licensed; see `LICENSE`.  Zork story and trademarks remain property of Activision.

> *“It is pitch dark. You are likely to be eaten by a grue.”* — Stay luminous!

