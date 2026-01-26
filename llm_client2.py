# ========================================
# ==============================Some usefull point =================
# Autoregressive => the model generates text one token at a time, and each new token is predicted using all the previous tokens.


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
                api_key = "9834732hfjdshfkjhfkjdshfkj",
                base_url="https://api.openrouter.com/v1",
                # here I don't add model name because I want to set it dynamically while making requests and also add auto model selct logic based on request which cursir does
                # model="",

            )

    # close the already initiated client 
    async def close(self)->None:
        if self._client:
            await self._client.close()
            self._client = None

    async def chat_completion(self,message:list[dict[str,Any]],stream:bool=True):

        # These are two different methods to handle streaming and non-streaming responses it is private methods 
        if stream:
            self._stream_response
        else:
            self._non_stream_response


#  PRIVTAE METHODS TO GET RESPONSES
    async def _stream_response(self):
        pass
    async def _non_stream_response(self):
        pass


        


