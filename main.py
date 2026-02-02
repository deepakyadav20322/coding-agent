

import asyncio
from client.llm_client2 import LLMClient



async def main():
    llm_client = LLMClient()
    message=[
            {"role":"user","content":"Hello, how are you?"  }
        ]
    async for event in llm_client.chat_completion(
      message,
        False
    ):
        print(event)

    print('done..')

# This runs the async function properly
if __name__ == "__main__":
    result = asyncio.run(main())
    # print(f"Response: {result}")