
from pathlib import Path
from typing import Any
from codeagent.config.config import Config
from platformdirs import user_config_dir,user_data_dir
import tomli
import tomli_w 
from codeagent.utils.errors import ConfigError 
import logging

# Project level config file name => .claude-code-type-agent
# System level config file name => C:\Users\DEEPAK YADAV\AppData\Local\claude-code-type-agent\claude-code-type-agent

logger = logging.getLogger(__name__)


CONFIG_FILE_NAME = "config.toml"
AGENT_MD_FILE = "AGENT.MD"

def get_data_dir() -> Path:
    return Path(user_config_dir("claude-code-type-agent"))

# user related configuration
def get_config_dir()->Path:
    # TODO:
    # Automatically create config directory if missing.
    # This prevents users from manually creating folders.
    # config_dir.mkdir(parents=True, exist_ok=True)
    return Path(user_config_dir("claude-code-type-agent"))

def get_data_directory()->Path:
    return Path(user_data_dir("claude-code-type-agent"))

# system related configuration
def get_system_config_path()->Path:
    return get_config_dir() / CONFIG_FILE_NAME

def _get_project_config(cwd: Path) -> Path | None:
    current = cwd.resolve()
    agent_dir = current / ".claude-code-type-agent"

    if agent_dir.is_dir():
        config_file = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file

    return None

def _get_agent_md_files(cwd: Path) -> Path | None:
    current = cwd.resolve()

    if current.is_dir():
        agent_md_file = current / AGENT_MD_FILE
        if agent_md_file.is_file():
            content = agent_md_file.read_text(encoding="utf-8")
            return content

    return None


# This used for deep merging of two dicts because in config we have nested dicts and we want to merge them properly without losing any data {this happen when I override the system config with project config then if I have nested dicts in system config}
def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def _parse_toml(path:Path):
    try:
        with path.open("rb") as f:
            data = tomli.load(f)
            # this return a dictionary of data
            return data
        
    except tomli.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {path}: {e}", config_file=str(path)) from e
    except (OSError, IOError) as e:
        raise ConfigError(f"Error reading config file {path}: {e}", config_file=str(path)) from e

def load_config(cwd:Path|None)->Config:
    cwd = cwd or Path.cwd()

    system_path = get_system_config_path()
        # 👇 ADD DEBUG HERE
    # print("System config path:", system_path)
    # print("File exists:", system_path.exists())


    config_dict: dict[str, Any] = {}
    api_key_origin:str | None = None

    # if your system path is other than file{menas folder} then you delaing with wrong things
    if system_path.is_file():
        try:
             config_dict = _parse_toml(system_path)
             if "api_key" in config_dict:
                 api_key_origin = str(system_path)
        except ConfigError :
            logger.warning(f"Skipping invalid system config: {system_path}")

    project_path = _get_project_config(cwd)
    if project_path:
        try:
            project_config_dict = _parse_toml(project_path)
            config_dict = _merge_dicts(config_dict, project_config_dict)
            if "api_key" in project_config_dict:
                api_key_origin = str(project_path)
        except ConfigError:
            logger.warning(f"Skipping invalid system config: {system_path}")

    config_dict["api_key_origin"] = api_key_origin
    if "cwd" not in config_dict:
        config_dict["cwd"] = cwd


    if "developer_instructions" not in config_dict:
        agent_md_content = _get_agent_md_files(cwd)
        if agent_md_content:
            config_dict["developer_instructions"] = agent_md_content

    try:
        config = Config(**config_dict)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e

    return config





# ------------------------------------------------------------------------
# NEW: helpers used by `codeagent login` and `codeagent config show`
# ------------------------------------------------------------------------

def load_system_config_raw() -> dict[str, Any]:
    """Read the raw system TOML as a dict (or {} if it doesn't exist yet).
    Used by `codeagent login` so we don't clobber other settings the user
    already has saved (model name, temperature, etc.) when we write the key.
    """
    path = get_system_config_path()
    if path.is_file():
        try:
            return _parse_toml(path)
        except ConfigError:
            logger.warning(f"System config is invalid, starting fresh: {path}")
            return {}
    return {}


def save_system_config(data: dict[str, Any]) -> Path:
    """Write a dict back to the system config TOML.
    Creates the parent directory if it doesn't exist (your old TODO).
    Returns the path written to, so the CLI can show it to the user.
    """
    path = get_system_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(data, f)
    return path













# TODO:for load_config():
# If config.toml does not exist, automatically generate a default config file.
# This helps first-time users get started without manual setup.
#
# Example default config:
#
# [model]
# name = "openrouter/free"
# temperature = 1
#
# max_turns = 100
# max_tool_output_tokens = 50000
#
# Implementation idea:
# if not system_path.exists():
#     system_path.write_text(DEFAULT_CONFIG_TEMPLATE)