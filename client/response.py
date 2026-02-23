#💀  it have a new sechema and new classes of events what a model can give/have 

# 💀 what is __future__ and why used and previosaly(before py3.9 version) how to handle that

#💀  class EventType(str,Enum):   => here how define the enum values without str and with str what difference ?



from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json
from typing import Any


@dataclass
class TextDelta:
    content:str | None = None

    def __str__(self):
        return self.content
    



class StreamEventType(str,Enum):
    TEXT_DELTA = "text_delta"
    MESSAGE_COMPLETE = "message_complete"
    ERROR = "error"

    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_COMPLETE = "tool_call_complete"



# this is uses a lot because it used to determin how much time to wait for to do some sort of compaction or other operations so this store all the statstics related token useage 
@dataclass
class TokenUsage:
    prompt_tokens:int = 0
    completion_tokens:int = 0
    total_tokens:int = 0
    cached_tokens:int = 0

    # how to two token classes are used to added
    # it work like a.__add__(b) where a is self toekn and b is other toekn
    def __add__(self,other:TokenUsage):
        return TokenUsage(
            prompt_tokens = self.prompt_tokens + other.prompt_tokens,
            completion_tokens = self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_tokens=  self.cached_tokens + other.cached_tokens,
        )

@dataclass
class ToolCallDelta:
    call_id:str
    name:str|None = None,
    arguments_delta:str = ""

    
@dataclass
class ToolCall:
    call_id:str
    name:str|None = None,
    arguments:str = ""


@dataclass
class StreamEvent:
    type:StreamEventType
    text_delta: TextDelta | None = None
    error: str | None = None
    finish_reason:str |None = None
    tool_call_delta:ToolCallDelta |None=None
    tool_call:ToolCall |None = None
    usage: TokenUsage |None = None

    
@dataclass
class ToolResultMessage:
    tool_call_id:str
    content:str
    error: bool = False

    def to_openai_message(self)->dict[str,Any]:
        return{
            "role": "tool",
            "too_call_id":self.tool_call_id,
            "content":self.content,
        }

def parse_tool_call_arguments(arguments_str: str) -> dict[str, Any]:
    if not arguments_str:
        return {}

    try:
        return json.loads(arguments_str)
    except json.JSONDecodeError:
        return {"raw_arguments": arguments_str}