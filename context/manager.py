

from dataclasses import  dataclass, field

from typing import Any
from config.config import Config
from prompts.system import get_system_prompt
from utils.text import count_tokens

@dataclass
class MessageItem:
    role:str
    content:str

    tool_call_id:str|None = None,
    tool_calls: list[dict[str,Any]] =  field(default_factory=list)

    token_count:int |None = None

    # this method is used to convert in the dict formate like what openai api expects 
    def to_dict(self)->dict[str,Any]:
        result:dict[str,Any] = {"role":self.role}

        if self.tool_call_id:
            result['tool_call_id'] = self.tool_call_id

        if self.tool_calls:
            result['tool_calls']= self.tool_calls   

        if self.content:
            result["content"] = self.content
    
        # According to need we also next add tool calls related stufs here
        return result

class ContextManager:
    def __init__(self,config:Config,user_memory:str | None):
        self._system_prompt = get_system_prompt(config,user_memory)
        self._messages:list[MessageItem] = []
        self.config = config
        # self._model_name = 'nvidia/nemotron-3-nano-30b-a3b:free'  # Currentaly I hardcoded this letter Itake it from config
        self._model_name = self.config.model_name  # Currentaly I hardcoded this letter Itake it from config
        # self._model_name = 'nvidia/nemotron-3-nano-30b-a3b:free'  # Currentaly I hardcoded this letter Itake it from config

    def add_user_message(self,content:str)->None:
        # safe_content = content or ""  # here don't pass empty string then you get unexpected resposes in terminal
        safe_content = content 

        item = MessageItem(
            role="user",
            content=safe_content,
            token_count= count_tokens(
                safe_content,
                self._model_name,
            ),
        )

        self._messages.append(item)

    def add_assistant_message(
            self,
            content:str,
            tool_calls:list[dict[str,any]] | None = None,        # this used to mentain and aware about tool calls and it's content in context also with assistance and user  messages 
            )->None:
        item = MessageItem(
            role="assistant",
            content=content or "",
            token_count= count_tokens(
                content or "", # here I am doing this because if content is None then it will give error in count_tokens function so I am passing empty string in that case {this possible empty string when I do tool call and tool return None or empty string then it will come here with content None so to avoid that I am doing this }
                self._model_name,
            ),
            tool_calls=tool_calls or []
        )

        self._messages.append(item)

    def add_tool_result(self,tool_call_id:str,content:str)->None:
        item = MessageItem(
            role="tool",
            content=content,
            tool_call_id = tool_call_id,
            token_count=count_tokens(content,self._model_name)
        )

        self._messages.append(item)

    # Getting all the messages in the dict formate like what openai api expects (And these used to pass to our Agent we defined in agent.py)
    def get_messages(self)->list[dict[str,Any]]:
        messages= []

        if self._system_prompt:
            messages.append({
                "role":"system",
                "content":self._system_prompt,
            })
        for items in self._messages:
            messages.append(items.to_dict())

        return messages