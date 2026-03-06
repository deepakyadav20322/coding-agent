
# if you have multiple sessions then you have multiple context manager


from pathlib import Path
from typing import AsyncGenerator

from agent.events import AgentEvent, AgentEventType
from client.llm_client2 import LLMClient
from client.response import StreamEventType, ToolCall, ToolResultMessage
from config.config import Config
from context.manager import ContextManager
from tools.registry import create_default_registry


class Agent:
    def __init__(self,config: Config):
        self.config = config
        self.client = LLMClient(config=self.config)
        self.context_manager = ContextManager(config=self.config)
        self.tool_registry = create_default_registry()
    async def run(self, message:str):
        yield AgentEvent.agent_start(message)
#   Add user message to the context and send it to the llm client and get the response as stream of events and then convert those events into agent event and yield it to the caller of this function
        self.context_manager.add_user_message(message)

        final_response: str | None = None
        async for event in self._agentic_loop():
            yield event
        
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
        
        yield AgentEvent.agent_end(final_response)

        # Agentic loop is multi turn conversation which come letter
    async def _agentic_loop(self)->AsyncGenerator[AgentEvent,None]:
        # messages=[{"role":"user","content":"Hello, how are you?"  }]

        max_turns = self.config.max_turns

        for turn_num in range(max_turns):

            response_text = ""

            tool_calls:list[ToolCall] = []

            tool_schemas = self.tool_registry.get_schemas()
            async for event in self.client.chat_completion(
                self.context_manager.get_messages(),
                tools = tool_schemas if tool_schemas else None,
                stream=True 
            ):

                # print(event)
                if event.type == StreamEventType.TEXT_DELTA:
                    if event.text_delta:
                        content  = event.text_delta.content 
                        response_text += content or ""
                        yield AgentEvent.text_delta(content)
                elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                    if event.tool_call:
                        tool_calls.append(event.tool_call)
                elif event.type == StreamEventType.ERROR:
                    yield AgentEvent.agent_error(event.error or "Unknown error occured")
                
            self.context_manager.add_assistant_message(
                response_text or None,
                [
                    {
                    "id":tc.call_id,
                    "type":"function",
                    "function":{
                        "name":tc.name,
                        "arguments":str(tc.arguments),
                    },
                    }
                    for tc in tool_calls

                ]
            
                )
            if response_text:
                yield AgentEvent.text_complete(response_text)

            # If no tool calls to do it means return from turn loop {what pydentic ai also do}
            if not tool_calls:
                return

            
            tool_call_result:list[ToolResultMessage] = []  

            
            for tool_call in tool_calls:
            # displaying to the uswrs when tool call start and what are the arguments for that tool call
                print(f"DEBUG tool_call.arguments: {tool_call.arguments}")
                yield AgentEvent.tool_call_start(
                    call_id=tool_call.call_id,
                    name=tool_call.name or "unknown_tool",
                    arguments=tool_call.arguments or {}
                )
                
                # This result may be success or failoour{error}
                result = await self.tool_registry.invoke(
                    tool_call.name ,
                    tool_call.arguments,
                    # Path.cwd()
                    self.config.cwd,
                ) 
                
                yield AgentEvent.tool_call_complete(
                    tool_call.call_id,
                    tool_call.name,
                    result,
                )

                tool_call_result.append(ToolResultMessage(
                    tool_call_id=tool_call.call_id,
                    content= result.to_model_output(),
                    error= not result.success

                ))
            
            for tool_result in tool_call_result:
                self.context_manager.add_tool_result(
                    tool_result.tool_call_id,
                    tool_result.content
                )



    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()

               









# 💁💁💁💁💁💁💁💁💁💁💁💁 4:34:000 / 4:35:22


# 7:27:00     turn