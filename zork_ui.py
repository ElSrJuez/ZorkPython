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
            text = Text(line)
            # Use render_lines to get actual line count
            segments = self.console.render_lines(text, self.console.options.update_width(content_width))
            line_count = len(segments)
            
            if total_rendered_lines + line_count > target_height:
                break
            
            result_lines.insert(0, line)
            total_rendered_lines += line_count
        
        return "\n".join(result_lines)

    def render(self):
        # Calculate available height
        prompt_height = 4
        body_height = self.console.size.height - prompt_height - 2  # -2 for panel borders
        
        # Calculate approximate panel widths based on ratio (2:3)
        total_width = self.console.size.width
        left_width = int(total_width * 0.4)  # 2/(2+3) = 0.4
        right_width = int(total_width * 0.6)  # 3/(2+3) = 0.6
        
        # Get visible lines accounting for wrapping
        left_text = self._get_renderable_lines(self.zork_lines, left_width, body_height)
        right_text = self._get_renderable_lines(self.ai_lines, right_width, body_height)
        
        self.layout["left"].update(
            Panel(left_text, title="Zork Output", border_style="green")
        )
        self.layout["right"].update(
            Panel(right_text, title="AI Output", border_style="cyan")
        )
        self.layout["prompt"].update(
            Panel(self.prompt_text, title="Prompt", border_style="magenta")
        )
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

    def append_ai(self, text: str):
        self.ai_lines.append(text)
        self.live.update(self.render())

if __name__ == "__main__":
    ui = RichZorkUI()
    ui.start()
    # Test with some long lines that will wrap
    for i in range(30):
        ui.append_zork(f"Room description line {i} - This is a longer line that might wrap depending on your terminal width")
        ui.append_ai(f"AI says: response {i} with some additional text that could cause wrapping")
        time.sleep(0.2)
    time.sleep(2)
    ui.stop()