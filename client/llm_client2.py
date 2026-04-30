# ========================================
# ==============================Some usefull point 👇👇👇👇=================
#💀 Autoregressive => the model generates text one token at a time, and each new token is predicted using all the previous tokens.
# 💀 what is coroutene in python
# 💀factory method is:=> A method that creates and returns an object for you.
# 💀 what is the difference between yield and retuen and what diff Generator and asyncgeneartor and how ans where usages
# 💀 what is difference between yield and return || difference between generator and  itreater 

# 💀 💀  WHAT IS DEPENDENCY MANAGEMENT HOW PEOPLE CREATE AND USE IT {7:12:00-7:13:00 SEC TIMIMG MENTION THIS TOPC IN VIDEO RIVAN RANWAT  }
# =========================

import asyncio
from typing import Any, AsyncGenerator
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from client.response import (StreamEventType, StreamEvent, TextDelta, TokenUsage, ToolCall, ToolCallDelta,parse_tool_call_arguments)
from config.config import Config

class LLMClient:
    def __init__(self,config: Config)->None :
        self._client : AsyncOpenAI | None = None
        self.max_retries: int =  3
        self.config = config    
    
    # instance method (Get the initiated client instace)
    def get_client(self)->AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                # api_key = "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",
                # base_url="https://openrouter.ai/api/v1",
                api_key = self.config.api_key,
                base_url=self.config.base_url,
                 default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "Claude Code Agent"
    }
                # here I don't add model name because I want to set it dynamically while making requests and also add auto model selct logic based on request which cursir does
                # model="",

            )
        return self._client

    # close the already initiated client 
    async def close(self)->None:
        if self._client:
            await self._client.close() 
            self._client = None

    # It generate the openai specs for tool call
    async def _build_tools(self,tools:list[dict[str,Any]]):
        return[
            {
                'type':'function',
                'function':{
                    'name':tool['name'],
                    'description':tool.get('description'),
                    'parameters':tool.get('parameters',{'type':'object','properties':{},},),
                }
            }
            for tool in tools
        ] 
    
    
    async def chat_completion(
        self,message:list[dict[str,Any]],
        tools:list[dict[str,Any]] | None = None,
        stream:bool=True
        )->AsyncGenerator[StreamEvent,None]:


        client = self.get_client() 
        # print("DEBUG messages:", message)
        kwargs = {
            # "model":"nvidia/nemotron-3-nano-30b-a3b:free",
            # "model": "openrouter/free",
            "model": self.config.model_name,
            # "model": "nvidia/nemotron-3-nano-30b-a3b:free",
            "messages":message,
            "stream":stream
        }

        if tools:
            kwargs['tools'] = await self._build_tools(tools)
            kwargs['tool_choice'] = "auto"

        for attempt in range(self.max_retries +1):
            try:
               
                # These are two different methods to handle streaming and non-streaming responses it is private methods 
                if stream:
                    async for event in self._stream_response(client,kwargs):
                        yield event
                else: 
                    event = await self._non_stream_response(client,kwargs)
                    yield event
                return
            except RateLimitError as e :
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(  
                    type = StreamEventType.ERROR,
                    error = f"Rate limit exceeded after {self.max_retries} attempts.",
                    )
                    # I am here return because we reached to our retry limit so no need to continue further
                    return
            except APIConnectionError as e :
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    print("REAL API CONNECTION ERROR:", e)
                    yield StreamEvent(  
                    type = StreamEventType.ERROR,
                    error = f"API connection error after {self.max_retries} attempts.",
                    )
                    return

            except APIError as e :
                print("REAL API ERROR:", e)
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(  
                    type = StreamEventType.ERROR,
                    error = f"API error after {self.max_retries} attempts.",
                    )
                    return
            except Exception as e:
                yield StreamEvent(  
                    type = StreamEventType.ERROR,
                    error = str(e),
                    )
                return


#  PRIVTAE METHODS TO GET RESPONSES
    async def _stream_response(self,
        client:AsyncOpenAI,
        kwargs:dict[str,Any],
    ) ->AsyncGenerator[StreamEvent,None]:
        # here we are using async for because the response is a stream of events
        # async for chunks in client.chat.completions.create(**kwargs):
        #         yield chunks

        response = await client.chat.completions.create(**kwargs)

        finish_reason: str | None = None
        usage: TokenUsage | None = None
        tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            #In streaming response only the last stream event have usages info. that;s why we check by hasstr

            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens,
                )
        #    may be choices come as empty list then that case handle here 
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(delta.content),
                )

            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index

                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            'id': tool_call_delta.id,
                            'name':'',
                            'arguments':''
                        }
                        if tool_call_delta.function:
                            if tool_call_delta.function.name:
                                tool_calls[idx]['name'] = tool_call_delta.function.name
                                yield StreamEvent(
                                    type=StreamEventType.TOOL_CALL_START,
                                    tool_call_delta=ToolCallDelta(
                                        call_id=tool_calls[idx]['id'],
                                        # name=tool_calls[idx]['name']
                                        name=tool_call_delta.function.name,
                                ) )
                            
                    if tool_call_delta.function.arguments:
                        print(
                                f"Before append arguments: {tool_calls[idx]['arguments']}"
                            )
                        tool_calls[idx]['arguments'] += tool_call_delta.function.arguments
                        print(
                f"After append arguments: {tool_calls[idx]['arguments']}"
            )
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_DELTA,
                            tool_call_delta=ToolCallDelta(
                                call_id=tool_calls[idx]['id'],
                                name=tool_calls[idx]['name'],
                                arguments_delta=tool_call_delta.function.arguments,
                            )
                        )
        for idx, tc in tool_calls.items():
            print(f"DEBUG final tool_calls dict: {tool_calls}")  # ← add this
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=parse_tool_call_arguments(tc["arguments"]),
                ),
            )


        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )
        
    async def _non_stream_response(self,client:AsyncOpenAI,kwargs:dict[str,Any]) ->StreamEvent:
        response  = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message =choice.message

        text_delta = None
        if message.content:
          text_delta = TextDelta(content=message.content)

        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=parse_tool_call_arguments(tc.function.arguments),
                    )
                )

        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens = response.usage.prompt_tokens,
                completion_tokens = response.usage.completion_tokens,
                total_tokens = response.usage.total_tokens,
                cached_tokens = response.usage.prompt_tokens_details.cached_tokens,
            )
        stream_event = StreamEvent(
            type = StreamEventType.MESSAGE_COMPLETE,
            text_delta= text_delta,
            finish_reason= choice.finish_reason,
            usage= usage,

        )

        return stream_event

        # print(response)


        


