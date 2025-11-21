"""Tkinter-based companion window for scene prompts/images."""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import tkinter as tk
    from tkinter import ttk
    _IMPORT_ERROR = None
else:  # pragma: no cover - runtime import
    try:
        import tkinter as tk  # type: ignore
        from tkinter import ttk  # type: ignore
    except ImportError as exc:
        tk = None  # type: ignore[assignment]
        ttk = None  # type: ignore[assignment]
        _IMPORT_ERROR = exc
    else:
        _IMPORT_ERROR = None


@dataclass
class PromptPreview:
    """Lightweight container for prompt metadata."""

    prompt: str
    negative_prompt: str
    seed: int


class ImageCompanionGUI:
    """Minimal Tkinter window that previews the next scene prompt."""

    def __init__(self, title: str = "Zork Scene Companion") -> None:
        self.title = title
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._root: Optional[Any] = None
        self._status_var: Optional[Any] = None
        self._prompt_widget: Optional[Any] = None
        self._ready_event = threading.Event()

    def start(self) -> None:
        """Launch the Tkinter window in a background thread."""
        if _IMPORT_ERROR is not None:
            raise RuntimeError("Tkinter is unavailable") from _IMPORT_ERROR
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=2)

    def stop(self) -> None:
        """Request termination of the Tkinter loop."""
        if self._root is None:
            return
        self._queue.put(("stop", ""))
        if self._thread and threading.current_thread() is not self._thread:
            self._thread.join(timeout=2)

    def set_status(self, message: str) -> None:
        """Display a status string beneath the title."""
        if self._root is None:
            return
        self._queue.put(("status", message))

    def show_prompt(self, preview: PromptPreview) -> None:
        """Render the latest prompt metadata in the pane."""
        if self._root is None:
            return
        self._queue.put(("prompt", preview))

    def _run_loop(self) -> None:
        if tk is None or ttk is None:
            self._ready_event.set()
            return
        self._root = tk.Tk()
        self._root.title(self.title)
        self._root.geometry("480x320")
        self._root.protocol("WM_DELETE_WINDOW", self.stop)

        container = ttk.Frame(self._root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        self._status_var = tk.StringVar(value="Waiting for scene context…")
        status_label = ttk.Label(container, textvariable=self._status_var)
        status_label.pack(anchor=tk.W, pady=(0, 10))

        self._prompt_widget = tk.Text(
            container,
            height=12,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self._prompt_widget.pack(fill=tk.BOTH, expand=True)

        self._ready_event.set()
        self._poll_queue()
        self._root.mainloop()

    def _poll_queue(self) -> None:
        if self._root is None:
            return
        try:
            while True:
                action, payload = self._queue.get_nowait()
                if action == "stop":
                    self._root.quit()
                    self._root = None
                    return
                if action == "status" and self._status_var is not None:
                    self._status_var.set(str(payload))
                if action == "prompt" and self._prompt_widget is not None:
                    self._render_prompt(payload)
        except queue.Empty:
            pass
        finally:
            self._root.after(50, self._poll_queue)

    def _render_prompt(self, payload: object) -> None:
        if self._prompt_widget is None:
            return
        self._prompt_widget.configure(state=tk.NORMAL)
        self._prompt_widget.delete("1.0", tk.END)
        if isinstance(payload, PromptPreview):
            text = (
                "Prompt:\n"
                f"{payload.prompt}\n\n"
                "Negative Prompt:\n"
                f"{payload.negative_prompt}\n\n"
                f"Seed: {payload.seed}"
            )
        else:
            text = str(payload)
        self._prompt_widget.insert(tk.END, text)
        self._prompt_widget.configure(state=tk.DISABLED)


__all__ = ["ImageCompanionGUI", "PromptPreview"]
