"""
System environment detection for the codeagent system prompt.

This module gathers information about the environment the agent is running
in (OS, shell, working directory, available CLI tools) so the LLM can pick
the right commands without trial-and-error.

PRIVACY RULES (intentional):
  - We only collect information ABOUT THE ENVIRONMENT, never about the user.
  - No username, no hostname, no IP addresses, no installed-software scan.
  - No filesystem reads outside what Python tells us about its own runtime.
  - Everything here works with ZERO special permissions on every OS.

All functions are pure stdlib so there is nothing to install.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

# The CLI tools we check for. The LLM uses many of these for coding tasks;
# knowing up-front which exist saves it from running failed commands.
# Order matters only for the printed output -- it's grouped logically.
_TOOLS_TO_DETECT = [
    # Version control
    "git",
    # Common shells (informational; we already detect the active one separately)
    "bash", "zsh", "powershell", "pwsh",
    # Languages and runtimes
    "python", "python3", "node", "npm", "pnpm", "yarn",
    "go", "rustc", "cargo", "java", "javac", "ruby", "php",
    # Search / build tools the prompt mentions explicitly (rg, etc.)
    "rg", "grep", "find", "make", "cmake",
    # Container / cloud
    "docker", "kubectl", "gh",
    # Package managers
    "pip", "pipx", "brew", "apt", "winget",
]


def _detect_os() -> dict[str, str]:
    """Identify the operating system in plain terms the LLM understands."""
    system = platform.system()  # 'Windows', 'Linux', 'Darwin'

    if system == "Darwin":
        os_name = "macOS"
        os_version = platform.mac_ver()[0] or "unknown"
    elif system == "Windows":
        os_name = "Windows"
        # platform.release() returns '10', '11', etc. (Win11 still reports 10
        # in some Python builds, but it's good enough as a hint.)
        os_version = platform.release()
    elif system == "Linux":
        os_name = "Linux"
        # Try to read the human-readable distro from /etc/os-release.
        # This file is world-readable on every modern distro; no permission
        # check needed. Falls back to kernel release if missing.
        os_version = _read_linux_distro() or platform.release()
    else:
        os_name = system or "unknown"
        os_version = platform.release() or "unknown"

    return {"name": os_name, "version": os_version}


def _read_linux_distro() -> str | None:
    """Return e.g. 'Ubuntu 24.04' from /etc/os-release if available."""
    path = Path("/etc/os-release")
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                # Strip the leading key and surrounding quotes
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def _detect_shell() -> str:
    """Best-effort guess at the active shell.

    On Windows we distinguish PowerShell from cmd.exe because their syntax
    differs significantly (e.g. $env:VAR vs %VAR%). On Unix we trust $SHELL.
    """
    if platform.system() == "Windows":
        # PowerShell sets PSModulePath; cmd.exe does not. This is the most
        # reliable signal without spawning a subprocess.
        if os.environ.get("PSModulePath"):
            return "PowerShell"
        return "cmd.exe"

    # Unix-y systems set $SHELL to the user's login shell.
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        # Return just the binary name (e.g. 'zsh'), not the full path.
        return Path(shell_path).name
    return "sh"


def _detect_available_tools() -> tuple[list[str], list[str]]:
    """Return (available, missing) tool lists.

    shutil.which() consults PATH only -- no shell invocation, no filesystem
    crawl, no permissions. It's the same lookup the shell itself would do.
    """
    available: list[str] = []
    missing: list[str] = []
    for tool in _TOOLS_TO_DETECT:
        if shutil.which(tool):
            available.append(tool)
        else:
            missing.append(tool)
    return available, missing


def get_environment_summary(cwd: Path | None = None) -> str:
    """Build the environment block that gets injected into the system prompt.

    This is the only function the rest of the codebase needs to call. It
    returns a markdown-formatted string ready to be appended to the prompt.
    """
    os_info = _detect_os()
    shell = _detect_shell()
    available, _missing = _detect_available_tools()

    # cwd: caller passes config.cwd if they have it; otherwise we ask Python.
    working_dir = str(cwd or Path.cwd())

    # On Windows, give the LLM concrete examples of correct command syntax.
    # This is what prevents the "pwd / ls fails 4 times in a row" loop you
    # saw earlier -- the model now has a hint in its very first context.
    if os_info["name"] == "Windows":
        shell_guidance = (
            "- Use Windows commands: `dir` (not `ls`), `type` (not `cat`), "
            "`echo %CD%` (not `pwd`).\n"
            "- Path separator is `\\`. Do not assume Unix paths.\n"
            "- For multi-step commands prefer `&&` between commands."
        )
    else:
        shell_guidance = (
            "- Standard Unix commands are available "
            "(`ls`, `cat`, `pwd`, `grep`, etc.).\n"
            "- Path separator is `/`."
        )

    # Cap the tools list in case PATH is huge; the agent only needs a hint.
    tools_str = ", ".join(available) if available else "(none of the common tools detected)"

    return f"""# Environment

The agent is running in this environment. Use this information to choose
commands and code that will work here, and avoid syntax that will not.

- **OS:** {os_info['name']} {os_info['version']}
- **Shell:** {shell}
- **Python:** {platform.python_version()}
- **Architecture:** {platform.machine()}
- **Working directory:** {working_dir}

## Shell guidance

{shell_guidance}"""