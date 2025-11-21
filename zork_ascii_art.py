"""
Generate colorful ASCII art of a Zork scene using recent sample output.

This script reads a recorded playthrough JSONL file under
`res/test_run/player/<playername>.jsonl`, builds a concise scene
description from the recent lines, then calls the same local AI
inference API used by the game to produce an ASCII art depiction.

Output is displayed with Rich in a colorful panel.

Usage (from repo root):
	python zork_ascii_art.py --input res/test_run/player/Malaria.jsonl --lines 40
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Reuse the existing local model client & alias
from zork_ai import client, manager, alias


console = Console()


def iter_transactions(jsonl_path: Path):
	"""Yield transactions from JSONL as tuples.

	Yields either ("command", command_str) or
	("printed", printed_text, source_func, previous_command).
	"""
	if not jsonl_path.exists():
		raise FileNotFoundError(f"Sample log not found: {jsonl_path}")

	prev_cmd: Optional[str] = None
	with jsonl_path.open("r", encoding="utf-8") as f:
		for raw in f:
			raw = raw.strip()
			if not raw:
				continue
			try:
				obj = json.loads(raw)
			except json.JSONDecodeError:
				continue

			msg = obj.get("message")
			if isinstance(msg, str) and msg.strip():
				prev_cmd = msg.strip()
				yield ("command", prev_cmd)

			printed = obj.get("printed_messages")
			if isinstance(printed, list):
				for pair in printed:
					if (
						isinstance(pair, list)
						and len(pair) >= 1
						and isinstance(pair[0], str)
						and pair[0].strip()
					):
						text = pair[0].strip()
						source = pair[1] if len(pair) > 1 and isinstance(pair[1], str) else ""
						yield ("printed", text, source, prev_cmd)


def build_ascii_art_prompt(scene_lines: List[str]) -> List[dict[str, str]]:
	"""Construct messages for the chat completion that request ASCII art.

	We intentionally bypass the JSON schema here and ask for an ASCII
	depiction with strict formatting, based on the recent scene.
	"""
	excerpt = "\n".join(scene_lines)
	system = (
		"You are an in-world artist for a text adventure. "
		"Create a compact ASCII art depiction of the current scene described by the log. "
		"Stay complementary and avoid spoilers or inventing unseen objects. "
		"Constraints: 40–60 columns wide, 12–20 rows tall, use only standard ASCII. "
		"Output STRICTLY a single fenced code block with just the art (no commentary)."
	)
	user = (
		"Recent scene log (game outputs interleaved with commands):\n\n"
		f"{excerpt}\n\n"
		"Please render one ASCII art panel representing the location and salient objects."
	)
	return [
		{"role": "system", "content": system},
		{"role": "user", "content": user},
	]


def build_ascii_art_prompt_single(prev_cmd: Optional[str], printed_text: str, source_func: str) -> List[dict[str, str]]:
	"""Messages requesting ASCII art for a single transaction."""
	prev = f"> {prev_cmd}" if prev_cmd else "(no previous command)"
	system = (
		"You are an in-world artist for a text adventure. "
		"Create a compact ASCII art depiction of the current moment. "
		"Stay complementary and avoid spoilers or inventing unseen objects. "
		"Constraints: 40–60 columns wide, 12–20 rows tall, ASCII only. "
		"Output STRICTLY a single fenced code block with just the art."
	)
	user = (
		f"Previous command: {prev}\n"
		f"Game output: {printed_text}\n"
		f"Source function: {source_func}\n\n"
		"Render one ASCII panel representing this moment."
	)
	return [
		{"role": "system", "content": system},
		{"role": "user", "content": user},
	]


def extract_code_block(text: str) -> str:
	"""Extract content from the first triple-backtick code block; else return raw text."""
	stripped = text.strip()
	if stripped.startswith("```"):
		# find closing fence
		end = stripped.find("```", 3)
		if end != -1:
			inner = stripped[3:end]
			# drop optional language hint on first line
			inner_lines = inner.splitlines()
			if inner_lines and inner_lines[0].lower().strip() in {"ascii", "text", "json"}:
				return "\n".join(inner_lines[1:]).rstrip()
			return inner.rstrip()
	return stripped


def call_model_for_art(scene_lines: List[str], max_tokens: int = 800) -> str:
	"""Invoke the local model to generate ASCII art for the scene."""
	messages = build_ascii_art_prompt(scene_lines)
	kwargs = {
		"model": manager.get_model_info(alias).id,  # type: ignore[attr-defined]
		"messages": messages,
		"temperature": 0.6,
		"max_tokens": max_tokens,
	}
	resp = client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
	msg = resp.choices[0].message
	content = msg.content if isinstance(msg.content, str) else ""
	art = extract_code_block(content)
	return art


def call_model_for_art_single(prev_cmd: Optional[str], printed_text: str, source_func: str, max_tokens: int = 400) -> str:
	"""Invoke the local model to generate ASCII art for a single transaction."""
	messages = build_ascii_art_prompt_single(prev_cmd, printed_text, source_func)
	kwargs = {
		"model": manager.get_model_info(alias).id,  # type: ignore[attr-defined]
		"messages": messages,
		"temperature": 0.6,
		"max_tokens": max_tokens,
	}
	resp = client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
	msg = resp.choices[0].message
	content = msg.content if isinstance(msg.content, str) else ""
	return extract_code_block(content)


def render_colorful_art(art: str) -> None:
	"""Render ASCII art with a simple color gradient in a Rich panel."""
	lines = art.splitlines() or [art]
	palette = [
		"bold bright_cyan",
		"bright_blue",
		"bright_magenta",
		"bright_yellow",
		"bright_green",
		"cyan",
		"magenta",
		"yellow",
		"green",
		"white",
	]

	styled_lines: List[Text] = []
	for i, line in enumerate(lines):
		style = palette[i % len(palette)]
		styled_lines.append(Text(line, style=style))

	art_text = Text("\n").join(styled_lines)
	panel = Panel(art_text, title="Zork ASCII Art", border_style="bright_cyan")
	console.print(panel)


def main() -> None:
	parser = argparse.ArgumentParser(description="Generate per-transaction Zork ASCII art from a sample JSONL log.")
	parser.add_argument(
		"--input",
		type=Path,
		default=Path("res/test_run/player/Malaria.jsonl"),
		help="Path to sample JSONL log",
	)
	args = parser.parse_args()

	try:
		tx_iter = iter_transactions(args.input)
	except Exception as e:
		console.print(f"[red]Failed to read JSONL:[/] {e}")
		return

	for tx in tx_iter:
		if not tx:
			continue
		tag = tx[0]
		if tag == "command":
			cmd = tx[1] if len(tx) > 1 else ""
			console.rule(f"[bold cyan]Command[/]: {cmd}")
			continue
		if tag == "printed":
			printed_text = tx[1] if len(tx) > 1 else ""
			source_func = tx[2] if len(tx) > 2 else ""
			prev_cmd = tx[3] if len(tx) > 3 else None
			try:
				art = call_model_for_art_single(prev_cmd, printed_text, source_func)
			except Exception as e:
				console.print(f"[yellow]Model error:[/] {e} — showing text instead")
				art = printed_text or "(no text)"

			header = Text(f"{source_func or 'scene'}", style="bold bright_magenta")
			if prev_cmd:
				header.append(f"  · prev: {prev_cmd}", style="dim")
			console.print(header)
			render_colorful_art(art)
			console.print()


if __name__ == "__main__":
	main()

