from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.segment import Segment
import time

class RichZorkUI:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="body", ratio=1),
            Layout(name="prompt", size=4),
        )
        self.layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=3),
        )
        self.zork_lines = []
        self.ai_lines = []
        self.prompt_text = ""
        self.ai_color_toggle = False  # Track color alternation for AI blocks



    def _get_renderable_lines(self, lines, panel_width, target_height):
        """
        Get lines that fit in target_height, accounting for wrapping.
        Returns the most recent lines that fit.
        """
        if not lines:
            return ""
        
        # Account for panel borders (2 chars on each side)
        content_width = panel_width - 4
        
        # Work backwards from the end
        result_lines = []
        total_rendered_lines = 0
        
        for line in reversed(lines):
            # Render the text to see how many lines it takes
            text = Text.from_markup(line)
            # Use render_lines to get actual line count
            segments = self.console.render_lines(text, self.console.options.update_width(content_width))
            line_count = len(segments)
            
            if total_rendered_lines + line_count > target_height:
                break
            
            result_lines.insert(0, line)
            total_rendered_lines += line_count
        
        return "\n".join(result_lines)

    def render(self):
        # Calculate available height accounting for prompt and panel borders
        prompt_height = 4
        body_height = self.console.size.height - prompt_height - 2  # two border lines

        # Determine column widths (40% / 60%)
        total_width = self.console.size.width
        left_width = int(total_width * 0.4)
        right_width = total_width - left_width - 1  # adjust for divider

        # Get wrapped, scrollable text for each pane
        left_raw = self._get_renderable_lines(self.zork_lines, left_width, body_height)
        right_raw = self._get_renderable_lines(self.ai_lines, right_width, body_height)

        left_text = Text.from_markup(left_raw)
        right_text = Text.from_markup(right_raw)

        self.layout["left"].update(Panel(left_text, title="Zork Output", border_style="green"))
        self.layout["right"].update(Panel(right_text, title="AI Output", border_style="cyan"))
        self.layout["prompt"].update(Panel(self.prompt_text, title="Prompt", border_style="magenta"))
        return self.layout


    def start(self):
        self.live = Live(self.render(), console=self.console, refresh_per_second=10)
        self.live.start()

    def set_prompt(self, text: str):
        self.prompt_text = text
        if hasattr(self, "live"):
            self.live.update(self.render())

    def read_prompt(self, prompt: str = "") -> str:
        import sys, msvcrt
        self.set_prompt(prompt)
        buffer: list[str] = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                line = "".join(buffer)
                self.set_prompt("")
                self.console.print()
                return line
            elif ch in ("\b", "\x7f"):
                if buffer:
                    buffer.pop()
            else:
                buffer.append(ch)
            self.set_prompt(prompt + "".join(buffer))

    def stop(self):
        self.live.stop()

    def append_zork(self, text: str):
        self.zork_lines.append(text)
        self.live.update(self.render())

    def start_ai_message(self, separator: str | None = None):
        """Begin a fresh AI message block, optionally prefixed by a separator.

        Also toggles the colour used for this message so consecutive blocks
        are visually distinct.
        """
        self.ai_color_toggle = not self.ai_color_toggle  # Toggle color for new block
        if separator and self.ai_lines:
            # separator on its own line
            self.ai_lines.append(separator)
        # Start a new block with an opening style tag
        style = "cyan" if self.ai_color_toggle else "magenta"
        self.ai_lines.append(f"[{style}]")

        if hasattr(self, "live"):
            self.live.update(self.render())


    def finalize_ai_message(self, full_text: str | None = None):
        """Hook for any post-message handling (currently no-op)."""
        # Close the style tag for the current block
        if self.ai_lines and not self.ai_lines[-1].endswith("[/]"):
            self.ai_lines[-1] += "[/]"
        if hasattr(self, "live"):
            self.live.update(self.render())

        # Speak narration using Piper if available and text seems plain
        if full_text:
            try:
                # Heuristic: skip if it looks like JSON (has braces)
                if "{" not in full_text and "}" not in full_text:
                    from zork_voice import speak
                    speak(full_text)
            except Exception as exc:  # noqa: BLE001
                from zork_logging import system_log
                system_log(f"Voice playback failed: {exc}")


    def write_ai(self, text: str):
        """Stream text into the current (last) AI message block."""
        if not self.ai_lines:
            # Ensure a block exists
            self.ai_lines.append("")
        # Append text directly; retain newlines within the same block
        self.ai_lines[-1] += text
        
        self.live.update(self.render())


    def append_ai(self, text: str):
        self.ai_lines.append(text)
        self.live.update(self.render())

if __name__ == "__main__":
    ui = RichZorkUI()
    ui.start()
    # Test with some long lines that will wrap
    for i in range(30):
        ui.append_zork(f"Room description line {i} - This is a longer line that might wrap depending on your terminal width")
        
        # Start a new AI message block, then stream into it
        ui.start_ai_message()
        ui.write_ai(f"AI says: response {i} with some additional text that could cause wrapping\n")
        ui.write_ai(f"This is part 2 of response {i}.")
        
        time.sleep(0.2)
    time.sleep(2)
    ui.stop()