

from pydantic import BaseModel, Field, model_validator
from pathlib import Path
import os

class ModelConfig(BaseModel):
    name:str  = "openrouter/free"
    temperature:float = Field(default=1,ge=0.0,le=2.0)
    context_window:int = 256000


class ShellEnvironMentPolicy(BaseModel):
    ignore_default_excludes: bool= False
    exclude_patterns:list[str] = Field(default_factory=lambda:["*KEY*","*TOKEN*","*SECRET*"])
    set_vars : dict[str,str] = Field(default_factory=dict)  # used to setup the overriding env variables for llm shell context

class Config(BaseModel):
    model:ModelConfig =  Field(default_factory=ModelConfig)
    cwd:Path= Field(default_factory=Path.cwd)

    shell_environment: ShellEnvironMentPolicy = Field(default_factory=ShellEnvironMentPolicy)

    # It is used to protect infinite loop of ai.
    max_turns :int = 100

    # max_tool_output_tokens: int = 50000

    developer_instructions:str |None = None
    user_instructions:str |None = None

    debug:bool= False

    # NEW: real fields, loaded from TOML when present.
    # We use different field names (api_key_value / base_url_value) because
    # the public access points api_key / base_url are properties below.
    # The `alias=` lets TOML write `api_key = "..."` and have it bind here.
    api_key_value: str | None = Field(default=None, alias="api_key")
    base_url_value: str | None = Field(default=None, alias="base_url")


    # Required so Pydantic accepts BOTH the alias ("api_key" from TOML)
    # AND the field name ("api_key_value" if used in Python).
    model_config = {"populate_by_name": True}

    # Which config file the api_key was loaded from (filled in by the loader).
    # Used only to tell the user WHERE their expired key lives.
    api_key_origin: str | None = None
    

    
    
    @property
    def api_key_from_env(self) -> bool:
        return bool(os.environ.get("API_KEY"))

    @property
    def api_key_source(self) -> str:
        """Human-readable answer to: where is the key in use coming from?"""
        if self.api_key_from_env:
            return "environment variable API_KEY"
        if self.api_key_value:
            return f"config file {self.api_key_origin}" if self.api_key_origin else "config file"
        return "nowhere (no key is set)"

    # @property
    # def api_key(self)->str|None:
    #     return os.environ.get("API_KEY")

    # @property
    # def base_url(self)->str|None:
    #     return os.environ.get("BASE_URL")

    @property
    def api_key(self) -> str | None:
        # PRIORITY: env var first (one-off override), then TOML field.
        env_value = os.environ.get("API_KEY")
        if env_value:
            return env_value
        return self.api_key_value

    @property
    def base_url(self) -> str | None:
        env_value = os.environ.get("BASE_URL")
        if env_value:
            return env_value
        return self.base_url_value
    
    @property
    def model_name(self)->str :
        return self.model.name
    
    @model_name.setter
    def model_name(self,value:str)->str:
        self.model.name  = value

    @property
    def temperature(self)->float:
        return self.model.temperature
    
    @temperature.setter
    def temperature(self,value:str)->str:
        self.model.temperature  = value
    
    def validate(self)->list[str]:
        errors:list[str] = []
        # if not self.api_key:
        #     errors.append("API_KEY is not set in environment variables.")
        if not self.api_key:
            errors.append(
                "API key not found. Run `codeagent login` to save one, "
                "or set the API_KEY environment variable."
            )
        
        if not self.cwd.exists():
            errors.append(f"Current working directory {self.cwd} does not exist.")

        return errors




# ==>06:40:0000