# ========================================
# ==============================Some usefull point 👇👇👇👇=================
#💀 Autoregressive => the model generates text one token at a time, and each new token is predicted using all the previous tokens.
# 💀 what is coroutene in python
# 💀factory method is:=> A method that creates and returns an object for you.
# 💀 what is the difference between yield and retuen and what diff Generator and asyncgeneartor and how ans where usages
# 💀 what is difference between yield and return || difference between generator and  itreater 


# =========================

import asyncio
from typing import Any, AsyncGenerator
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from client.response import EventType, StreamEvent, TextDelta, TokenUsage

class LLMClient:
    def __init__(self)->None :
        self._client : AsyncOpenAI | None = None
        self.max_retries: int =  3
    
    # instance method (Get the initiated client instace)
    def get_client(self)->AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key = "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",
                base_url="https://openrouter.ai/api/v1",
                # here I don't add model name because I want to set it dynamically while making requests and also add auto model selct logic based on request which cursir does
                # model="",

            )
        return self._client

    # close the already initiated client 
    async def close(self)->None:
        if self._client:
            await self._client.close()
            self._client = None
    
    async def chat_completion(
        self,message:list[dict[str,Any]],
        stream:bool=True)->AsyncGenerator[StreamEvent,None]:

        client = self.get_client() 
        kwargs = {
            "model":"nvidia/nemotron-3-nano-30b-a3b:free",
            "messages":message,
            "stream":stream
        }

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
                    type = EventType.ERROR,
                    error = f"Rate limit exceeded after {self.max_retries} attempts.",
                    )
                    # I am here return because we reached to our retry limit so no need to continue further
                    return
            except APIConnectionError as e :
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(  
                    type = EventType.ERROR,
                    error = f"API connection error after {self.max_retries} attempts.",
                    )
                    return

            except APIError as e :
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(  
                    type = EventType.ERROR,
                    error = f"API error after {self.max_retries} attempts.",
                    )
                    return
            except Exception as e:
                yield StreamEvent(  
                    type = EventType.ERROR,
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
                    type=EventType.TEXT_DELTA,
                    text_delta=TextDelta(delta.content),
                )
          
        yield StreamEvent(
            type=EventType.MESSAGE_COMPLETE,
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

        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens = response.usage.prompt_tokens,
                completion_tokens = response.usage.completion_tokens,
                total_tokens = response.usage.total_tokens,
                cached_tokens = response.usage.prompt_tokens_details.cached_tokens,
            )
        stream_event = StreamEvent(
            type = EventType.MESSAGE_COMPLETE,
            text_delta= text_delta,
            finish_reason= choice.finish_reason,
            usage= usage,

        )

        return stream_event

        # print(response)


        


