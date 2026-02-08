#💀  it have a new sechema and new classes of events what a model can give/have 

# 💀 what is __future__ and why used and previosaly(before py3.9 version) how to handle that

#💀  class EventType(str,Enum):   => here how define the enum values without str and with str what difference ?



from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


@dataclass
class TextDelta:
    content:str | None = None

    def __str__(self):
        return self.content
    



class StreamEventType(str,Enum):
    TEXT_DELTA = "text_delta",
    MESSAGE_COMPLETE = "message_complete",
    ERROR = "error"



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
class StreamEvent:
    type:StreamEventType
    text_delta: TextDelta | None = None
    error: str | None = None
    finish_reason:str |None = None
    usage: TokenUsage |None = None
    