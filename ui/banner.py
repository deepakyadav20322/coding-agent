"""
Startup banner for codeagent.

Prints a big ASCII-art "CODE AGENT" header above the welcome panel.
Implemented with only the `rich` library (already a dependency) -- no
extra installs needed, no internet, works on every terminal `rich` supports.

The art is a hand-picked block font that's readable down to ~60 columns wide.
The colors fade across the letters (left-to-right gradient) which is what
modern CLIs like Claude Code use.
"""

from __future__ import annotations

from rich.console import Console
from rich.text import Text


# 5-line ASCII art for "CODE AGENT". 57 chars wide. Embedded as a raw string
# so backslashes don't get interpreted as escape sequences.
_BANNER_LINES: list[str] = [
    r"  ____ ___  ____  _____      _    ____ _____ _   _ _____ ",
    r" / ___/ _ \|  _ \| ____|    / \  / ___| ____| \ | |_   _|",
    r"| |  | | | | | | |  _|     / _ \| |  _|  _| |  \| | | |  ",
    r"| |__| |_| | |_| | |___   / ___ \ |_| | |___| |\  | | |  ",
    r" \____\___/|____/|_____| /_/   \_\____|_____|_| \_| |_|  ",
]


def _gradient_colors(steps: int) -> list[str]:
    """Generate a list of hex colors fading from blue -> magenta -> orange.

    `steps` is how many colors we need (= width of the widest banner line).
    Returns hex strings like '#4f7cff' that rich can apply directly.
    """
    # Two gradient stops. Adjust these tuples to recolor the banner.
    # We blend through them linearly.
    stops = [
        (0x4F, 0x7C, 0xFF),   # cool blue
        (0xB5, 0x5C, 0xFF),   # purple
        (0xFF, 0x8A, 0x4C),   # warm orange
    ]

    colors: list[str] = []
    # Each segment of the gradient covers an equal portion of the width.
    segments = len(stops) - 1
    per_segment = max(steps // segments, 1)

    for s in range(segments):
        r1, g1, b1 = stops[s]
        r2, g2, b2 = stops[s + 1]
        for i in range(per_segment):
            t = i / per_segment  # 0.0 at start of segment, ~1.0 at end
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            colors.append(f"#{r:02x}{g:02x}{b:02x}")

    # Pad with the final color if we came up short due to integer division.
    while len(colors) < steps:
        r, g, b = stops[-1]
        colors.append(f"#{r:02x}{g:02x}{b:02x}")

    return colors


def render_banner(console: Console) -> None:
    """Print the gradient ASCII banner to the given console.

    Safe to call before anything else -- it just prints text.
    """
    # The widest line determines how many gradient steps we need so each
    # column of every line uses a consistent color.
    width = max(len(line) for line in _BANNER_LINES)
    colors = _gradient_colors(width)

    # Blank line above for breathing room from the previous shell output.
    console.print()

    for line in _BANNER_LINES:
        # Build a rich Text where each character has its column's color.
        # Spaces get a color too but they're invisible, so it's free.
        text = Text()
        for i, char in enumerate(line):
            text.append(char, style=f"bold {colors[i]}")
        console.print(text)

    # Tagline below the art. The em-dash + dim style mimic Claude Code's
    # "Anthropic's AI coding agent" subtitle.
    console.print()
    console.print(
        Text("  a cli coding agent  -  type /help for commands", style="dim italic"),
    )
    console.print()