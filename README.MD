# Claude Code Type Terminal Agent

A terminal-based AI coding agent built from start in Python — designed to autonomously read files, write code, and execute shell commands {more tools comming soon..} through a conversational CLI interface. Inspired by the architecture of tools like Claude Code and OpenAI Codex CLI.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Running the Agent](#running-the-agent)
- [How It Works](#how-it-works)
- [Built-in Tools](#built-in-tools)
- [Design Decisions](#design-decisions)
- [Known Limitations & TODOs](#known-limitations--todos)

---

## Overview

Claude Type Agent is a fully custom AI coding agent that runs in your terminal. You send it a message — it decides which tools to call, executes them, processes the results, and keeps reasoning until it completes the task. No UI, no browser, just a clean terminal interface powered by any OpenAI-compatible LLM via [OpenRouter](https://openrouter.ai).

The project was built to deeply understand how agentic AI systems work internally — including streaming LLM responses, tool call/result cycles, context management, and configuration layering.

---

## Architecture

The agent follows a clean, layered architecture where each module has a single responsibility:

```
User Input (CLI)
      │
      ▼
   CLI / TUI  ──────────────────────────── Rich terminal display
      │
      ▼
    Agent  ──────────────────────────────── Agentic loop (multi-turn)
      │
      ├── Session  ───────────────────────── Holds client, context, registry per session
      │       │
      │       ├── LLM Client  ────────────── Streams responses from OpenRouter API
      │       ├── Context Manager  ────────── Manages message history + system prompt
      │       └── Tool Registry  ──────────── Registers and dispatches tool calls
      │
      └── Tools  ──────────────────────────── read_file | write_file | shell
```

**Request lifecycle:**

1. User types a message in the terminal.
2. The CLI passes it to the `Agent`, which adds it to the `ContextManager`.
3. The `Agent` calls the `LLMClient`, which streams the response token-by-token.
4. If the LLM decides to call a tool, the `ToolRegistry` validates and executes it.
5. The tool result is added back to the context, and the loop continues.
6. Once the LLM produces a final text response with no tool calls, the turn ends.

---

## Features

- **Agentic loop** — the agent autonomously decides to call tools, processes results, and continues reasoning across multiple turns until the task is complete.
- **Real-time streaming** — LLM responses stream token-by-token to the terminal via async generators.
- **Built-in tools** — file reading (with line ranges), file writing (with diff output), and shell command execution (with safety blocklist).
- **Pluggable tool framework** — tools are defined using abstract base classes and Pydantic schemas, making it straightforward to add new tools or future MCP (Model Context Protocol) integrations.
- **Layered configuration** — TOML-based config with three-tier priority: CLI args → project-level config → system-level config.
- **Context window management** — structured message history with token counting, system prompt injection, and tool result formatting compatible with the OpenAI messages API.
- **Rich TUI** — terminal UI built with the `rich` library, showing streaming output, tool call start/complete events, file diffs, exit codes, and error states in a readable format.
- **Safety blocklist** — dangerous shell commands (`rm -rf /`, fork bombs, disk formatters, etc.) are blocked before execution.
- **Cross-platform** — handles Windows (`cmd.exe`) and Unix (`/bin/bash`) shell execution paths.
- **Interactive and single-prompt modes** — run with a prompt argument for a one-shot task, or without for a persistent interactive session.
- **AGENT.md support** — place an `AGENT.md` file in your project directory to inject project-specific instructions into the agent's system prompt automatically.

---

## Project Structure

```
claude-type-agent/
│
├── main.py                    # Entry point — CLI setup, interactive/single-prompt modes
│
├── agent/
│   ├── agent.py               # Core agentic loop logic
│   ├── session.py             # Per-session state (client, context, tool registry)
│   └── events.py              # AgentEvent types emitted during a run
│
├── client/
│   ├── llm_client2.py         # Async streaming LLM client (OpenAI-compatible)
│   └── response.py            # Response models (StreamEvent, ToolCall, TokenUsage)
│
├── context/
│   └── manager.py             # Message history, token counting, system prompt builder
│
├── prompts/
│   └── system.py              # System prompt sections (identity, security, operational)
│
├── tools/
│   ├── base.py                # Abstract Tool base class, ToolResult, ToolKind, FileDiff
│   ├── registry.py            # ToolRegistry — register, validate, and invoke tools
│   └── builtin/
│       ├── read_file.py       # read_file tool
│       ├── write_file.py      # write_file tool
│       ├── shell.py           # shell tool with safety blocklist
│       └── __init__.py        # Exports all built-in tools
│
├── config/
│   ├── config.py              # Config and sub-models (Pydantic)
│   └── loader.py              # TOML loader, config merging, AGENT.md reader
│
├── ui/
│   └── tui.py                 # Rich-based terminal UI rendering
│
├── utils/
│   ├── errors.py              # Custom exception types
│   ├── paths.py               # Path resolution, binary file detection
│   └── text.py                # Token counting, text truncation
│
├── .claude-code-type-agent/
│   └── config.toml            # Project-level config (committed to repo)
│
└── .env                       # API key and base URL (not committed)
```

---

## Prerequisites

- Python 3.12+
- An [OpenRouter](https://openrouter.ai) account and API key (or any OpenAI-compatible API endpoint)

---

## Setup & Installation

**1. Clone the repository**

```bash
git clone https://github.com/deepakyadav20322/coding-agent.git
cd coding-agent
```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

> Key dependencies: `httpx`, `pydantic`, `click`, `rich`, `tomli`, `platformdirs`, `tiktoken`

**4. Set environment variables**

The agent reads its API credentials from environment variables at runtime. You can set them in your shell or create a `.env` file (loaded manually — there is no automatic dotenv loading currently).

```bash
# Windows (Command Prompt)
set API_KEY=your-openrouter-api-key
set BASE_URL=https://openrouter.ai/api/v1

# macOS / Linux
export API_KEY=your-openrouter-api-key
export BASE_URL=https://openrouter.ai/api/v1
```

---

## Configuration

The agent uses a three-tier configuration system. Settings are merged in this priority order (highest wins):

```
CLI arguments  >  Project config  >  System config  >  Defaults
```

### System config (global, per user)

Located at:
- **Windows:** `C:\Users\<user>\AppData\Roaming\claude-code-type-agent\config.toml`
- **macOS/Linux:** `~/.config/claude-code-type-agent/config.toml`

Create this file manually if it does not exist.

```toml
[model]
name = "openrouter/auto"
temperature = 1

max_turns = 100
```

### Project config (per project)

Place a `config.toml` file inside a `.claude-code-type-agent/` directory at the root of your project:

```
your-project/
└── .claude-code-type-agent/
    └── config.toml
```

Example project config:

```toml
[model]
name = "mistralai/mistral-7b-instruct:free"
temperature = 0.7

max_turns = 50

[shell_environment]
set_vars = { NODE_ENV = "development" }
```

### AGENT.md — project instructions

Create an `AGENT.md` file in your project root to inject custom instructions into the agent's system prompt. Useful for setting coding conventions, file structure notes, or task context:

```markdown
# Project Instructions

- This is a FastAPI project. All routes go in `app/routes/`.
- Use type hints on all functions.
- Do not modify `requirements.txt` directly — use pip and regenerate.
```

### Config reference

| Key | Default | Description |
|-----|---------|-------------|
| `model.name` | `openrouter/auto` | Model identifier (any OpenAI-compatible model string) |
| `model.temperature` | `1` | Sampling temperature (0.0 – 2.0) |
| `model.context_window` | `256000` | Maximum context window size in tokens |
| `max_turns` | `100` | Maximum agentic loop iterations before stopping |
| `shell_environment.exclude_patterns` | `["*KEY*","*TOKEN*","*SECRET*"]` | Env var patterns to strip before passing to shell tools |
| `shell_environment.set_vars` | `{}` | Env vars to inject into shell tool environment |
| `debug` | `false` | Enable verbose debug logging |

---

## Running the Agent

### Interactive mode

Run without any arguments to start an ongoing session. Type your task and the agent will work through it:

```bash
python main.py
```

```
╭─────────────────────────────╮
│  AI Agent                   │
│  model: openrouter/auto     │
│  cwd: /home/user/my-project │
│  commands: /help /exit      │
╰─────────────────────────────╯

[user]> refactor the parse_csv function in utils.py to handle empty rows
```

### Single-prompt mode

Pass a prompt directly as an argument for a one-shot task:

```bash
python main.py "list all Python files in this directory and summarize what each one does"
```

### Change working directory

Use `--cwd` to point the agent at a specific project directory:

```bash
python main.py --cwd /path/to/your/project "add error handling to app.py"
```

---

## How It Works

### The agentic loop

The core of the agent is a multi-turn loop in `agent/agent.py`. Each turn:

1. Sends the current message history to the LLM with the available tool schemas.
2. Streams the response — text deltas are forwarded to the TUI immediately as they arrive.
3. If the LLM emits one or more tool calls, each tool is validated and executed in sequence.
4. Tool results are added to the context as `tool` role messages.
5. The loop repeats with the updated context until the LLM returns a response with no tool calls.

The loop is bounded by `max_turns` in config to prevent infinite reasoning cycles.

### Streaming

The `LLMClient` uses `httpx` with async streaming to read server-sent events (SSE) from the API. Text content and tool call arguments are assembled incrementally from delta chunks. This is what allows the terminal to display the agent's response as it is generated rather than waiting for the full response.

### Tool execution

Every tool extends the abstract `Tool` base class and defines:
- A `name` and `description` (sent to the LLM as part of the tool schema)
- A `schema` — a Pydantic `BaseModel` that defines and validates the tool's input parameters
- A `kind` — classifies the tool as `READ`, `WRITE`, `SHELL`, `NETWORK`, or `MEMORY`
- An `execute` method — the async function that performs the actual work

The `ToolRegistry` wraps execution with parameter validation before calling `execute`, and catches unexpected exceptions to prevent the agent from crashing mid-session.

### Context management

The `ContextManager` maintains a list of `MessageItem` objects representing the full conversation history. It handles:
- User messages
- Assistant responses (with optional tool call blocks)
- Tool results (keyed by `tool_call_id` to match the OpenAI API format)
- System prompt injection (composed from identity, security, operational sections, and any AGENT.md content)

Token counts are tracked per message using `tiktoken` to support future context window trimming.

---

## Built-in Tools

### `read_file`
Reads a text file and returns its content with line numbers. Supports `offset` and `limit` parameters to read specific line ranges in large files. Rejects binary files and files over 10 MB.

```
read_file(path="src/main.py", offset=10, limit=50)
```

### `write_file`
Writes content to a file, creating it (and any missing parent directories) if it does not exist. On overwrite, generates a unified diff of the old and new content shown in the TUI.

```
write_file(path="src/utils.py", content="...", create_directories=True)
```

### `shell`
Executes a shell command asynchronously in a subprocess, with a configurable timeout (default 120s, max 600s). Captures both stdout and stderr. Strips sensitive environment variables matching patterns like `*KEY*`, `*TOKEN*`, `*SECRET*` before execution. Blocks a hardcoded list of destructive commands.

```
shell(command="pytest tests/ -v", timeout=60)
```

**Blocked commands include:** `rm -rf /`, `rm -rf ~`, `dd if=/dev/zero`, `mkfs`, `fdisk`, fork bombs, `shutdown`, `reboot`, and similar destructive operations.

---

## Design Decisions

**Why abstract base classes for tools instead of plain functions?**
Using `abc.ABC` gives each tool a consistent interface (schema, execute, validate, kind), makes the registry uniform regardless of tool type, and provides a clear extension point for future tool types like MCP integrations.

**Why Pydantic for tool schemas?**
Pydantic handles parameter validation, type coercion, and JSON schema generation all in one place. The generated schema is passed directly to the LLM as the tool definition, so the same model that validates input also defines what the LLM is allowed to send.

**Why per-session state instead of global state?**
The `Session` class (holding the LLM client, context manager, and tool registry) is created fresh for each conversation. This means multiple sessions can run independently without shared state, which is the correct foundation for future multi-session support.

**Why OpenRouter instead of a direct API?**
OpenRouter provides a single OpenAI-compatible endpoint that proxies dozens of models — including free-tier models — making it easy to swap models without changing any code, just the config.

**Why async throughout?**
Streaming LLM responses and subprocess execution both benefit from async I/O. Using `asyncio` and `httpx` with async streaming means the event loop is never blocked while waiting for tokens or subprocess output.

---

## Known Limitations & TODOs

- **No persistence** — conversation context is in-memory only. Sessions do not survive process restarts.
- **Config directory not auto-created** — the system config directory must be created manually on first run.
- **No `/config` CLI command** — planned: a `/config` command to open the config file in the default editor.
- **TUI breaks on terminal resize** — Rich layout does not currently reflow correctly after resize.
- **Patch-style file editing not implemented** — currently, `write_file` replaces the entire file. Targeted line-level edits (like those in Codex CLI) are planned.
- **No approval/confirmation flow in TUI** — the confirmation system is modeled in code but not yet wired into the interactive CLI prompt.
- **Token-based context trimming not active** — token counts are tracked per message but the context is not yet automatically trimmed when approaching the window limit.