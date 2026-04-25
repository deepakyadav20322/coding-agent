

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
    cwd:Path= Field(default_factory=Path.cwd())

    shell_environment: ShellEnvironMentPolicy = Field(default_factory=ShellEnvironMentPolicy)

    # It is used to protect infinite loop of ai.
    max_turns :int = 100

    # max_tool_output_tokens: int = 50000

    developer_instructions:str |None = None
    user_instructions:str |None = None

    debug:bool= False

    @property
    def api_key(self)->str|None:
        return os.environ.get("API_KEY")

    @property
    def base_url(self)->str|None:
        return os.environ.get("BASE_URL")
    
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
        if not self.api_key:
            errors.append("API_KEY is not set in environment variables.")
        
        if not self.cwd.exists():
            errors.append(f"Current working directory {self.cwd} does not exist.")

        return errors




# ==>06:40:0000