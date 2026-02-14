

from dataclasses import dataclass
from typing import Any
from prompts.system import get_system_prompt
from utils.text import count_tokens

@dataclass
class MessageItem:
    role:str
    content:str
    token_count:int |None = None

    # this method is used to convert in the dict formate like what openai api expects 
    def to_dict(self)->dict[str,Any]:
        result:dict[str,Any] = {"role":self.role}

        if self.content:
            result["content"] = self.content
    
        # According to need we also next add tool calls related stufs here
        return result

class ContextManager:
    def __init__(self):
        self._system_prompt = get_system_prompt()
        self._messages:list[MessageItem] = []
        self.model_name = 'nvidia/nemotron-3-nano-30b-a3b:free'  # Currentaly I hardcoded this letter Itake it from config

    def add_user_message(self,content:str)->None:
        safe_content = content or ""  # here 

        item = MessageItem(
            role="user",
            content=safe_content,
            token_count= count_tokens(
                safe_content,
                self.model_name,
            ),
        )

        self._messages.append(item)

    def add_assistant_message(self,content:str)->None:
        item = MessageItem(
            role="assistant",
            content=content or "",
            token_count= count_tokens(
                content or "",
                self.model_name,
            ),
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