
"""
Turns provider HTTP errors into clear, actionable messages for the user.

OpenRouter status codes (https://openrouter.ai/docs/api-reference/errors):
    401 -> API key invalid, expired, disabled or revoked
    402 -> account has no credits left
    403 -> input flagged by moderation
    429 -> rate limited
    5xx -> provider/model temporarily down
"""

import os

from config.config import Config

AUTH_ERROR = 401
NO_CREDITS = 402

# Only these are worth retrying; every other 4xx will fail the same way again.
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def provider_message(body: object, fallback: str) -> str:
    """Pull the human-readable message out of the provider's error body."""
    if isinstance(body, dict) and body.get("message"):
        return str(body["message"])
    return fallback


def _is_openrouter(config: Config) -> bool:
    return "openrouter.ai" in (config.base_url or "")


def _remove_env_var_instructions() -> str:
    return (
        "   Your API_KEY environment variable overrides the saved key. Remove it:\n"
        "     Windows, this terminal:  set API_KEY=\n"
        "     Windows, permanently:    setx API_KEY \"\"  (then open a new terminal)\n"
        "     macOS / Linux:           unset API_KEY  (also delete it from ~/.bashrc / ~/.zshrc)"
    )


def auth_error_help(config: Config, detail: str) -> str:
    """Message shown when the provider rejects the API key (HTTP 401)."""
    keys_url = "https://openrouter.ai/keys" if _is_openrouter(config) else "your provider's dashboard"

    lines = [
        "Your API key was rejected. It is invalid, expired, or has been revoked.",
        f"Provider said: {detail}",
        "",
        f"Key currently in use comes from: {config.api_key_source}",
        "",
        "How to fix:",
        f"  1. Create a new key at {keys_url}",
        "  2. Save it with one of:",
        "       /login              (inside this session, no restart needed)",
        "       codeagent login     (from your terminal)",
    ]
    if config.api_key_from_env:
        lines.append("  3. " + _remove_env_var_instructions().lstrip())
    return "\n".join(lines)


def no_credits_help(config: Config, detail: str) -> str:
    """Message shown when the account is out of credits (HTTP 402)."""
    credits_url = (
        "https://openrouter.ai/settings/credits" if _is_openrouter(config) else "your provider's billing page"
    )
    return "\n".join([
        "Your account does not have enough credits for this request.",
        f"Provider said: {detail}",
        "",
        "How to fix:",
        f"  1. Add credits at {credits_url}",
        "  2. Or switch to a free model with /model",
    ])