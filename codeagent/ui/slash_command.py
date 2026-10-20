"""
Slash commands for the interactive agent loop.

Slash commands are special inputs starting with `/` that are handled by
codeagent itself rather than being sent to the LLM. Examples:
    /help       -- show available commands
    /model      -- switch the active model mid-session

To add a new command:
    1. Write a handler function below.
    2. Register it in SLASH_COMMANDS at the bottom of this file.

Each handler receives (config, console) and returns one of:
    'continue'  -- keep the agent loop running normally
    'exit'      -- break out of the loop (the caller will end the session)
"""

from __future__ import annotations

import os
from typing import Callable
from rich.console import Console

import re
from codeagent.tools.builtin.memory import MemoryTool

from codeagent.config.config import Config
from codeagent.config.loader import load_system_config_raw, save_system_config


# -----------------------------------------------------------------------------
# Fixed model presets. Edit this list to change what /model offers.
# -----------------------------------------------------------------------------
# Each entry: (label shown to user, OpenRouter model string).
# Keep this list short -- 3-5 items max -- so the menu stays scannable.
_MODEL_PRESETS: list[tuple[str, str, str]] = [
    # (display name,                           model id,                          description)

    ("OpenRouter Free Router",      "openrouter/free",                    "Auto-picks a free model per request. Quality varies."),
    ("Claude Sonnet 4.5 (best quality)",       "anthropic/claude-sonnet-4.5",     "Frontier model. Best reasoning, highest cost."),
    ("Claude Sonnet 5.5",           "anthropic/claude-sonnet-5.5",        "~$2 / $10. Excellent for coding agents."),
    ("GPT-4o-mini (cheap, fast)",              "openai/gpt-4o-mini",              "Strong quality, much lower cost."),
    ("Gemini 2.5 Flash",            "google/gemini-2.5-flash",            "~$0.30 / $2.50. Fast, large context."),

    ("Mistral Ministral 14B (free)",           "mistralai/ministral-14b-2512",    "Open-source, free on OpenRouter."),
]


# -----------------------------------------------------------------------------
# Handlers
# -----------------------------------------------------------------------------

def _cmd_help(config: Config, console: Console,args:str="") -> str:
    """Show the list of available slash commands."""
    console.print()
    console.print("[bold]Available commands[/bold]")
    # Build the list from the registry so adding a command auto-updates /help.
    for name, (handler, description) in SLASH_COMMANDS.items():
        console.print(f"  [cyan]{name:<10}[/cyan]  {description}")
    console.print()
    return "continue"


def _cmd_model(config: Config, console: Console,args:str="") -> str:
    """Show the model picker and switch model for the rest of the session."""
    console.print()
    console.print(f"[bold]Current model:[/bold] {config.model_name}")
    console.print()
    console.print("[bold]Choose a model:[/bold]")
    for i, (label, model_id, desc) in enumerate(_MODEL_PRESETS, start=1):
        console.print(f"  [cyan]{i}.[/cyan] {label}")
        console.print(f"     [dim]{desc}[/dim]")
    console.print()

    # Use console.input so it stays consistent with the rest of the TUI.
    choice = console.input("Enter number (or press Enter to cancel): ").strip()

    if not choice:
        console.print("[dim]Cancelled.[/dim]")
        return "continue"

    if not choice.isdigit():
        console.print("[error]Not a number.[/error]")
        return "continue"

    index = int(choice) - 1
    if index < 0 or index >= len(_MODEL_PRESETS):
        console.print(f"[error]Pick a number between 1 and {len(_MODEL_PRESETS)}.[/error]")
        return "continue"

    label, model_id, _desc = _MODEL_PRESETS[index]

    # Mutate the live config object. llm_client2 reads config.model_name fresh
    # on every chat_completion() call, so the next user prompt picks this up
    # automatically -- no client rebuild needed.
    config.model_name = model_id
    console.print(f"[success]Switched to:[/success] {model_id}")
    return "continue"


def _cmd_login(config: Config, console: Console,args:str="") -> str:
    """Save a new API key without restarting the session."""
    console.print()
    api_key = console.input("Paste your new API key (hidden, Enter to cancel): ", password=True).strip()
    if not api_key:
        console.print("[dim]Cancelled.[/dim]")
        return "continue"

    data = load_system_config_raw()
    data["api_key"] = api_key
    data.setdefault("base_url", config.base_url or "https://openrouter.ai/api/v1")
    path = save_system_config(data)

    # Update the live config. The LLM client notices the key changed and
    # rebuilds itself on the next request.
    config.api_key_value = api_key
    config.api_key_origin = str(path)

    if os.environ.get("API_KEY"):
        # The env var would override the new key; drop it for this session.
        os.environ.pop("API_KEY", None)
        console.print(
            "[warning]The API_KEY environment variable was overriding your saved key. "
            "It is ignored for this session; remove it permanently with "
            "`setx API_KEY \"\"` (Windows) or by deleting it from your shell profile.[/warning]"
        )

    console.print(f"[success]Saved to:[/success] {path}")
    console.print("[dim]New key is active. Send your message again.[/dim]")
    return "continue"


# def _cmd_exit(config: Config, console: Console,args:str="") -> str:
#     """End the session cleanly."""
#     console.print("[dim]Goodbye![/dim]")
#     return "exit"
def _cmd_exit(config: Config, console: Console, args: str = "") -> str:
    """End the session cleanly."""
    return "exit"

def _cmd_memory(config: Config, console: Console, args: str = "") -> str:
    """List, add or delete saved memories (same store the `memory` tool uses)."""
    store = MemoryTool(config)          # reuse its load/save so the file path never drifts
    memory = store._load_memory()
    entries: dict[str, str] = memory.setdefault("entries", {})

    action, _, rest = args.strip().partition(" ")
    action = action.lower()
    rest = rest.strip()

    if action in ("", "list"):
        console.print()
        if not entries:
            console.print("[dim]No memories saved. Add one with /memory add <text>[/dim]")
            return "continue"
        console.print("[bold]Saved memories[/bold] [dim](used from the next session)[/dim]")
        for key, value in entries.items():
            console.print(f"  [cyan]{key}[/cyan]  {value}")
        console.print()
        console.print("[dim]Delete one with /memory delete <key>[/dim]")
        return "continue"

    if action == "add":
        if not rest:
            console.print("[error]Usage: /memory add <text>[/error]")
            return "continue"
        # Key = first few words, e.g. "give crisp answers" -> "give-crisp-answers".
        base = "-".join(re.findall(r"[a-z0-9]+", rest.lower())[:4]) or "note"
        key, n = base, 2
        while key in entries:
            key, n = f"{base}-{n}", n + 1
        entries[key] = rest
        store._save_memory(memory)
        console.print(f"[success]Saved[/success] [cyan]{key}[/cyan]: {rest}")
        console.print("[dim]It will be applied from your next session.[/dim]")
        return "continue"

    if action in ("delete", "del", "rm"):
        if not rest:
            console.print("[error]Usage: /memory delete <key>   (see keys with /memory)[/error]")
            return "continue"
        if rest not in entries:
            console.print(f"[error]No memory with key: {rest}[/error]  Run [cyan]/memory[/cyan] to see keys.")
            return "continue"
        removed = entries.pop(rest)
        store._save_memory(memory)
        console.print(f"[success]Deleted[/success] [cyan]{rest}[/cyan]: {removed}")
        return "continue"

    console.print("[error]Usage:[/error] /memory  |  /memory add <text>  |  /memory delete <key>")
    return "continue"

def _cmd_clear(config: Config, console: Console, args: str = "") -> str:
    """Clear the terminal screen."""
    console.clear()
    return "continue"

# -----------------------------------------------------------------------------
# Registry: maps the command name (with the leading slash) to:
#   (handler function, description shown by /help)
# -----------------------------------------------------------------------------
SLASH_COMMANDS: dict[str, tuple[Callable[[Config, Console], str], str]] = {
    "/help": (_cmd_help, "Show this help."),
    "/model": (_cmd_model, "Pick a model for this session."),
    "/memory": (_cmd_memory, "List memories. Also: /memory add <text>, /memory delete <key>"),
    "/login": (_cmd_login, "Save a new API key (e.g. when yours expired)."),
    "/clear": (_cmd_clear, "Clear the screen. (Menas /clear as written only wipes what you can see on screen.)"),
    "/exit": (_cmd_exit, "Quit codeagent."),
}


def is_slash_command(user_input: str) -> bool:
    """Return True if the input looks like a slash command."""
    return user_input.strip().startswith("/")


def handle_slash_command(user_input: str, config: Config, console: Console) -> str:
    """Dispatch a slash command. Returns 'continue' or 'exit'.

    Unknown commands print a hint and return 'continue' so the loop keeps
    running -- we don't want to send `/banana` to the LLM as a real prompt.
    """
    # Normalize: take just the first token (so `/model 2` would still match
    # /model, in case we add inline arguments later).
    # name = user_input.strip().split()[0].lower()
    name, _, args = user_input.strip().partition(" ")
    name = name.lower()

    entry = SLASH_COMMANDS.get(name)
    if entry is None:
        console.print(f"[error]Unknown command: {name}[/error]  Type [cyan]/help[/cyan] for the list.")
        return "continue"

    handler, _description = entry
    return handler(config, console, args.strip())