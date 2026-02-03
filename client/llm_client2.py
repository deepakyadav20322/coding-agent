# ========================================
# ==============================Some usefull point 👇👇👇👇=================
#💀 Autoregressive => the model generates text one token at a time, and each new token is predicted using all the previous tokens.
# 💀 what is coroutene in python
# 💀factory method is:=> A method that creates and returns an object for you.
# 💀 what is the difference between yield and retuen and what diff Generator and asyncgeneartor and how ans where usages



# =========================

from typing import Any, AsyncGenerator
from openai import AsyncOpenAI

from client.response import EventType, StreamEvent, TextDelta, TokenUsage

class LLMClient:
    def __init__(self)->None :
        self._client : AsyncOpenAI | None = None 
    
    # instance method (Get the initiated client instace)
    def get_client(self)->AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key = "sk-or-v1-",
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

    async def chat_completion(self,message:list[dict[str,Any]],stream:bool=True)->AsyncGenerator[StreamEvent,None]:

        client = self.get_client()
        kwargs = {
            "model":"nvidia/nemotron-3-nano-30b-a3b:free",
            "messages":message,
            "stream":stream
        }

        # These are two different methods to handle streaming and non-streaming responses it is private methods 
        if stream:
            async for event in self._stream_response(client,kwargs):
                yield event
        else: 
            event = await self._non_stream_response(client,kwargs)
            yield event
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
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens,
                )

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


        


