# ========================================
# ==============================Some usefull point 👇👇👇👇=================
#💀 Autoregressive => the model generates text one token at a time, and each new token is predicted using all the previous tokens.
# 💀 what is coroutene in python


# =========================

from typing import Any
from openai import AsyncOpenAI

class LLMClient:
    def __init__(self)->None :
        self._client : AsyncOpenAI | None = None 
    
    # instance method (Get the initiated client instace)
    def get_client(self)->AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key = "sdkjsfkdshfkjsdhfkjshfkjhskjf-testing",
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

    async def chat_completion(self,message:list[dict[str,Any]],stream:bool=True):

        client = self.get_client()
        kwargs = {
            "model":"nvidia/nemotron-3-nano-30b-a3b:free",
            "messages":message,
            "stream":stream
        }

        # These are two different methods to handle streaming and non-streaming responses it is private methods 
        if stream:
            await self._stream_response()
        else:
            await self._non_stream_response(client,kwargs)


#  PRIVTAE METHODS TO GET RESPONSES
    async def _stream_response(self):
        pass
    async def _non_stream_response(self,client:AsyncOpenAI,kwargs:dict[str,Any]):
        response  = await client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        text = None
        if message.content:
            pass 
        # 😊"=😊"😊"😊"

        print(response)


        


