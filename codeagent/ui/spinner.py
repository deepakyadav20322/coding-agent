"""
Transient status line shown while the agent is busy (model thinking,
tool running, model writing tool arguments).

It is redrawn by Rich's own refresh thread, so the animation and the
elapsed timer keep moving even when a tool blocks the event loop.
The line is erased (transient) as soon as stop() is called.
"""

from __future__ import annotations

import random
import time

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

THINKING_VERBS = [
    "Thinking", "Pondering", "Reasoning", "Considering",
    "Working", "Analyzing", "Brewing", "Cooking",
]

# tool name -> (verb, argument whose value is shown next to the verb)
TOOL_LABELS: dict[str, tuple[str, str | None]] = {
    "read_file": ("Reading", "path"),
    "write_file": ("Writing", "path"),
    "edit": ("Editing", "path"),
    "shell": ("Running", "command"),
    "list_dir": ("Listing", "path"),
    "grep": ("Searching for", "pattern"),
    "glob": ("Finding", "pattern"),
    "web_search": ("Searching the web for", "query"),
    "web_fetch": ("Fetching", "url"),
    "todos": ("Updating todos", None),
    "memory": ("Updating memory", None),
}

_VERB_ROTATE_SECONDS = 4
_REASONING_BUFFER_CHARS = 2000
_MAX_DETAIL_CHARS = 60


def _short(value: object, limit: int = _MAX_DETAIL_CHARS) -> str:
    text = " ".join(str(value).split())  # collapse newlines/whitespace
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _format_chars(count: int) -> str:
    return f"{count / 1000:.1f}k chars" if count >= 1000 else f"{count} chars"

def _reasoning_headline(buffer: str) -> str:
    """Pick one short line from the reasoning text to show in the status line.

    Prefers the latest **bold heading** (OpenAI-style reasoning summaries use
    these), otherwise the latest non-empty line.
    """
    import re
    headings = re.findall(r"\*\*(.+?)\*\*", buffer)
    if headings:
        line = headings[-1]
    else:
        lines = [l for l in buffer.splitlines() if l.strip()]
        if not lines:
            return ""
        line = lines[-1]
    line = " ".join(line.strip(" #*-`").split())
    if len(line) > _MAX_DETAIL_CHARS:
        line = "…" + line[-(_MAX_DETAIL_CHARS - 1):]   # keep the newest words visible
    return line

def _format_elapsed(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds}s" if seconds < 60 else f"{seconds // 60}m {seconds % 60:02d}s"


class StatusLine:
    def __init__(self, console: Console) -> None:
        self.console = console
        # Old Windows consoles cannot draw braille spinner frames.
        self._spinner = Spinner("line" if console.legacy_windows else "dots", style="info")
        self._live: Live | None = None
        self._phase_key: str | None = None
        self._started_at = 0.0
        self._label = ""
        self._detail = ""
        self._verbs: list[str] = []
        self._reasoning = ""

    @property
    def enabled(self) -> bool:
        # No animation when output is piped/redirected to a file.
        return self.console.is_terminal

    # ---------- public API ----------

    def thinking(self) -> None:
        self._show("thinking", label="", detail="")

    def reasoning(self, chunk: str) -> None:
        """Append thinking text; the status line shows its latest line."""
        if self._phase_key != "thinking":
            self.thinking()
        self._reasoning = (self._reasoning + chunk)[-_REASONING_BUFFER_CHARS:]

    def tool_preparing(self, name: str, arg_chars: int) -> None:
        verb, _ = TOOL_LABELS.get(name, (f"Preparing {name}", None))
        detail = f"({_format_chars(arg_chars)})" if arg_chars else ""
        self._show(f"prepare:{name}", label=f"{verb}…", detail=detail)

    def tool_running(self, name: str, arguments: dict) -> None:
        verb, arg_key = TOOL_LABELS.get(name, (f"Running {name}", None))
        value = arguments.get(arg_key) if arg_key else None
        label = f"{verb} {_short(value)}" if value else f"{verb}…"
        self._show(f"run:{name}", label=label, detail="")

    def stop(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None
        self._phase_key = None

    # ---------- internals ----------

    def _show(self, phase_key: str, label: str, detail: str) -> None:
        if not self.enabled:
            return
        if phase_key != self._phase_key:
            # New phase: restart the timer. Same phase: only refresh detail.
            self._phase_key = phase_key
            self._started_at = time.monotonic()
            self._reasoning = ""  
            if phase_key == "thinking":
                self._verbs = random.sample(THINKING_VERBS, len(THINKING_VERBS))
        self._label = label
        self._detail = detail
        if self._live is None:
            self._live = Live(
                console=self.console,
                get_renderable=self._render,
                refresh_per_second=12,
                transient=True,
                redirect_stdout=False,
                redirect_stderr=False,
            )
            self._live.start()

    def _render(self) -> Text:
        now = time.monotonic()
        elapsed = now - self._started_at
        label = self._label
        if self._phase_key == "thinking":
            verb = self._verbs[int(elapsed // _VERB_ROTATE_SECONDS) % len(self._verbs)]
            label = f"{verb}…"

        hint_parts = [_format_elapsed(elapsed)]
        if self._detail:
            hint_parts.insert(0, self._detail.strip("()"))
        hint = " · ".join(hint_parts)

        line = Text()
        line.append_text(self._spinner.render(now))
        line.append(" ")
        line.append(label, style="highlight")
        line.append(f"  ({hint} · ctrl+c to interrupt)", style="muted")
        return line