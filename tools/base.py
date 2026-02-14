# 😎😎 here I used dataclasses if I return someting time you can also return direct dict [ ... ] but fallow dataclass because we get nice type hint and more objext oriented structrure. 
# 😎 In schema I return dict and BaseModel type then If creat our own tool definetion and excution the I try to return baseModel type whiich make us to simplify type but If I used externak MCP then they are retur somethings of dict (which I don't know initially or all mcp return diff output ) hence I returun dict here also... 

# 💀 What is abstract class and how to define it and how to use and when I do get all kundali of this proerty.
#💀 What is @property in class and abc.abstractmethod or abc.abstractClassMethod.
# 💀 what is default factory keyword in dataclass decorator and fileld(....)-> metaData:dict[str,Any] = field(default_factory=dict)  
# 💀 What is difference between __dict__ and dict in metaData:dict[str,Any] = field(default_factory = dict), which one where and when use.





import abc 
from enum import Enum
from pydantic import BaseModel, ValidationError
from typing import Any
from dataclasses import dataclass ,field
from pathlib import Path


class Toolkind(str,Enum):
    READ="read",
    WRITE = "write",
    NETWORK = "network",
    SHELL = "shell",
    MCP = "MCP"


@dataclass
class ToolInvocation:
    params=dict[str,Any]
    cwd = Path              # it have path of current working directory the used in diffrent way (for example if I go to definde limit file scope the I can first get user permission the proceed that process..  more to do with this)

@dataclass 
class ToolResult:
    success:bool
    output:str
    error:str
    metaData:dict[str,Any] = field(default_factory=dict)



class Tool(abc.ABC):
    name: str = "base_tool",
    description:str = "Base Tool",
    kind:Toolkind  = Toolkind.READ

    def __init__(self)->None:
        super().__init__()

    @property
    def schema(self)->dict[str,Any] | type[BaseModel]:
        # all tool define must have the schema (custome have pydentic and inbult used amy have dic type then I chnage and utilize)
        return NotImplementedError("Tool must be define schema property and class attributr")
    
    # What should happen when the function/too going to excute
    @abc.abstractmethod
    async def excute(self,invocation:ToolInvocation)->ToolResult:
        pass


    # It is used to validate the tool parameteres that no any one pass other things to tool that create problems(like we need one str params but pass two params  of intiger like that ..) in excution And it only return list of string because it any validation error the it return that error other empty list means no any validation error all patameters are correct..        

    def validate_params(self,parmas:dict[str,Any])->list[str]:
        schema = self.schema

        if isinstance(schema,type) and issubclass(schema,BaseModel):
                try:
                    BaseModel(**parmas)

                except ValidationError as e:
                    errors = []

                    for error in e.errors():
                        field =".".join(str(x) for x in error.get("loc", []) )
                        msg = error.get("msg", "Validation error")
                        errors.append(f"Parameter '{field}': {msg}")

                    return errors
                except Exception as e:
                    return [str(e)]

        return []



