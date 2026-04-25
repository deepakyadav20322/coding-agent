


from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from client.response import TokenUsage
from tools.base import ToolResult



# It is an enum to use how many types we handle in agent event 
class AgentEventType(str,):
    # Agent lifecycle stuffs
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"
    # more lifecycle come letter...

    # text streaming
    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"

    # tool call streaming
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"



@dataclass
class AgentEvent:
    type:AgentEventType
    data:dict[str,Any] = field(default_factory=dict)

    @classmethod
    def agent_start(cls,message:str)->AgentEvent:
        return cls(type=AgentEventType.AGENT_START,
                  data={"message":message}
                )
    @classmethod
    def agent_end(cls,response:str|None = None,usage:TokenUsage|None = None,)->AgentEvent:
        return cls(
            type=AgentEventType.AGENT_END,
            data={"message":response,
                  "usage":usage.__dict__ if usage else None,

                  }

        )
    @classmethod
    def agent_error(cls,error:str,details:str|None = None)->AgentEvent:
        return cls(
            type=AgentEventType.AGENT_ERROR,
            data={"error":error,
                  "details":details or {}    #if details is not present then return empty dictonary {}
                  }
        )
    
    @classmethod
    def text_delta(cls,content:str|None)->AgentEvent:
        return cls(
            type=AgentEventType.TEXT_DELTA,
            data={"content":content}
        )
    
    @classmethod
    def text_complete(cls,content:str|None,)->AgentEvent:
        return cls(
            type= AgentEventType.TEXT_COMPLETE,
            data= {"content":content}
        )
    
    @classmethod
    def tool_call_start(cls,call_id:str,name:str,arguments:dict[str,Any]):

        return cls(
            type=AgentEventType.TOOL_CALL_START,
            data={
                "call_id":call_id,
                "name":name,
                "arguments":arguments   # like for read file it get limit, path , offset and other arguments in dict these are work as arguments for tool call
            }
        )
    @classmethod
    def tool_call_complete(cls,call_id:str,name:str, result:ToolResult):

        return cls(
            type=AgentEventType.TOOL_CALL_COMPLETE,
            data={
                "call_id":call_id,
                "name":name,
                "success":result.success,
                "error":result.error,
                "output":result.output,
                "metadata":result.metadata,
                 "diff":result.diff.to_diff() if result.diff  else None,
                "truncated":result.truncated,
                "exit_code": result.exit_code,
            }
        )
    


    # 5:08:15  :->   I am not getting sam output as in rivan ranwat