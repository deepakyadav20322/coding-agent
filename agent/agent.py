

from typing import AsyncGenerator

from agent.events import AgentEvent, AgentEventType
from client.llm_client2 import LLMClient
from client.response import StreamEventType


class Agent:
    def __init__(self):
        self.client = LLMClient()

    async def run(self, message:str):
        yield AgentEvent.agent_start(message)
#   Add user message to the context and send it to the llm client and get the response as stream of events and then convert those events into agent event and yield it to the caller of this function
        final_response: str | None = None
        async for event in self._agentic_loop():
            yield event
        
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
        
        yield AgentEvent.agent_end(final_response)

        # Agentic loop is multi turn conversation which come letter
    async def _agentic_loop(self)->AsyncGenerator[AgentEvent,None]:
        messages=[{"role":"user","content":"Hello, how are you?"  }]

        response_text = ""
        async for event in self.client.chat_completion(messages, True ):


            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content  = event.text_delta.content 
                    response_text += content or ""
                    yield AgentEvent.text_delta(content)

            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(event.error or "Unknown error occured")
                # return # Here if you want terminate the excuetion of agent b/c we get error but more you do handle this

        if response_text:
            yield AgentEvent.text_complete(response_text)

    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()

               
