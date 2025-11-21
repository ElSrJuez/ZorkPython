from __future__ import annotations

import argparse
import json
from itertools import zip_longest
from pathlib import Path
from typing import Iterable, List, Sequence

import zork_ai


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay a recorded player JSONL log and regenerate AI narration "
            "contexts using the current zork_ai pipeline."
        )
    )
    parser.add_argument(
        "--player-log",
        required=True,
        type=Path,
        help="Path to res/test_run/player/<session>.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination JSONL file (defaults to res/test_run/out/<session>.jsonl)",
    )
    parser.add_argument(
        "--max-log-lines",
        type=int,
        default=None,
        help=(
            "Optional override for how many transcript lines to feed into "
            "create_narration_context (defaults to config.json value)."
        ),
    )
    parser.add_argument(
        "--parse",
        action="store_true",
        help=(
            "After replay, print a three-column view comparing filtered game "
            "text, player commands, and narration from the generated run log."
        ),
    )
    return parser.parse_args()


def _derive_output_path(player_log: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    # Prefer sibling res/test_run/out directory when the log lives under res/test_run/player
    base_dir = player_log.parent.parent if player_log.parent.name == "player" else player_log.parent
    out_dir = base_dir / "out"
    return out_dir / f"{player_log.stem}.jsonl"


def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            yield json.loads(line)


def _append_printed(messages: Sequence[Sequence[str]], interactions: List[str]) -> List[str]:
    added: List[str] = []
    for text, _caller in messages:
        if not text:
            continue
        if interactions and interactions[-1] == text:
            continue
        interactions.append(text)
        added.append(text)
    return added


def _append_command(command: str, interactions: List[str]) -> str | None:
    cmd = command.strip()
    if not cmd:
        return None
    normalized = f"> {cmd.upper()}"
    interactions.append(normalized)
    return normalized


def _extract_narrations(run_log: Path) -> List[str]:
    narrations: List[str] = []
    for entry in _iter_jsonl(run_log):
        response = entry.get("response") if isinstance(entry, dict) else None
        if response is None:
            continue
        if isinstance(response, dict):
            value = response.get("narration")
            if isinstance(value, str):
                narrations.append(value)
            else:
                narrations.append(json.dumps(response, ensure_ascii=False))
        else:
            narrations.append(str(response))
    return narrations


def _print_three_columns(game_lines: Sequence[str], player_lines: Sequence[str], run_lines: Sequence[str]) -> None:
    def _clean(s: str) -> str:
        return s.replace("\n", "\\n")

    header = f"{'GAME':<40} | {'PLAYER':<20} | RUN"
    divider = "-" * len(header)
    print("\n" + header)
    print(divider)
    for game, player, run in zip_longest(game_lines, player_lines, run_lines, fillvalue=""):
        print(f"{_clean(game):<40} | {_clean(player):<20} | {_clean(run)}")


def main() -> None:
    args = _parse_args()
    player_log = args.player_log.resolve()
    if not player_log.is_file():
        raise SystemExit(f"Player log not found: {player_log}")

    output_path = _derive_output_path(player_log, args.output.resolve() if args.output else None)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Redirect zork_ai logging to the requested output file so the JSONL matches
    # the in-game format (request/response pairs).
    zork_ai.AI_LOG_PATH = output_path
    output_path.write_text("", encoding="utf-8")

    interactions: List[str] = []
    game_lines: List[str] = []
    player_lines: List[str] = []
    invocation_count = 0

    for entry in _iter_jsonl(player_log):
        if "printed_messages" in entry:
            added = _append_printed(entry["printed_messages"], interactions)
            if added:
                game_lines.extend(added)
            if added and interactions:
                zork_ai.create_narration_context(
                    interactions,
                    max_log_lines=args.max_log_lines,
                )
                invocation_count += 1
        elif "message" in entry:
            appended_cmd = _append_command(entry["message"], interactions)
            if appended_cmd:
                player_lines.append(appended_cmd)

    print(
        f"Replayed {invocation_count} narration calls -> {output_path}"
    )

    if args.parse:
        run_lines = _extract_narrations(output_path)
        _print_three_columns(game_lines, player_lines, run_lines)


if __name__ == "__main__":
    main()
