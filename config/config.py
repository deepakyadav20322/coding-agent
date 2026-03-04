

from dataclasses import Field,BaseModel
from pathlib import Path
import os

class ModelConfig(BaseModel):
    name:str  = "openrouter/free"
    temperature:float = Field(default=1,ge=0.0,le=2.0)
    context_window:int = 256000

class config(BaseModel):
    model:ModelConfig =  Field(default_factory=ModelConfig)
    cwd:Path= Field(default_factory=Path.cwd())

    max_turn :int = 100
    max_tool_output_tokens: int = 50000

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
        self.model_name  = value

    @property
    def temperature(self)->float:
        return self.model.temperature
    
    @temperature.setter
    def model_name(self,value:str)->str:
        self.temperature  = value



# ==>06:40:0000