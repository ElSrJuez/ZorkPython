"""
Zork AI – Controller layer

Implements the orchestrator outlined in
`scratchpad/completions_controller.md`.

Key ideas
---------
1. **Independence** – No direct dependency on OpenAI or Rich; it only relies
   on abstract interfaces:
      • ``CompletionService`` – provides :py:meth:`get_stream`
      • ``AIRenderer``        – provides ``start_ai_message``, ``write_ai``,
        and ``finalize_ai_message``.

2. **Streaming-agnostic** – Because :py:meth:`get_stream` is a generator that
   can yield any number of chunks (even just one), the controller works for
   both streaming and non-streaming completion implementations.

3. **Single Responsibility** – The controller coordinates the flow; it does *not*
   build prompts, perform logging, or render UI details itself.
"""
from __future__ import annotations

from collections.abc import Generator, Iterable
from typing import List, Protocol


# ---------------------------------------------------------------------------
# Protocols – minimal contracts expected from collaborators
# ---------------------------------------------------------------------------

class CompletionService(Protocol):
    """Abstract interface for any component that can supply LLM completions."""

    def get_stream(self, recent_lines: List[str]) -> Generator[str, None, str]:
        """Return a generator streaming chunks of the assistant reply.

        Parameters
        ----------
        recent_lines : list[str]
            Recent Zork transcript lines used for prompt construction.

        Yields
        ------
        str
            Next chunk of assistant text to display.

        Returns
        -------
        str
            The full assistant reply once the stream completes.
        """
        ...  # pragma: no cover


class AIRenderer(Protocol):
    """Subset of UI methods required by the controller."""

    def start_ai_message(self, separator: str | None = None) -> None: ...

    def write_ai(self, chunk: str) -> None: ...

    def finalize_ai_message(self, full_text: str) -> None: ...


# ---------------------------------------------------------------------------
# Controller / Orchestrator
# ---------------------------------------------------------------------------

SEPARATOR_LINE = "─" * 40


def ask_ai(
    ui: AIRenderer,
    recent_lines: List[str],
    svc: CompletionService,
    *,
    show_separator: bool = True,
) -> str:
    """Coordinate a single AI completion interaction.

    1. Signals the UI to start a new AI message (optionally with a separator).
    2. Streams chunks from ``svc.get_stream`` into the UI in real time.
    3. Ensures the UI is finalized and returns the full assistant reply.

    Parameters
    ----------
    ui : AIRenderer
        UI component (e.g. ``RichZorkUI``) handling rendering.
    recent_lines : list[str]
        Recent Zork transcript lines used to build the prompt. Passed straight
        to the completion service.
    svc : CompletionService
        Object handling prompt generation, LLM invocation and logging.
    show_separator : bool, default ``True``
        Whether to insert a horizontal rule before the new AI message.

    Returns
    -------
    str
        The complete assistant response text.
    """

    separator = SEPARATOR_LINE if show_separator else None
    ui.start_ai_message(separator)

    full_text_parts: List[str] = []
    stream = svc.get_stream(recent_lines)

    try:
        for chunk in stream:
            ui.write_ai(chunk)
            full_text_parts.append(chunk)
    finally:
        # Attempt to retrieve the return value of the generator (PEP 380).
        full_text: str
        try:
            stream.close()  # triggers StopIteration with .value if supported
        except RuntimeError:
            pass  # generator already exhausted or not started

        # Fallback if generator did not return a value
        full_text = "".join(full_text_parts)
        ui.finalize_ai_message(full_text)

    return full_text
