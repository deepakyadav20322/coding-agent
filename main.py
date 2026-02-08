

# import asyncio
# from client.llm_client2 import LLMClient



# async def main():
#     llm_client = LLMClient()
#     message=[
#             {"role":"user","content":"Hello, how are you?"  }
#         ]
#     async for event in llm_client.chat_completion(
#       message,
#         True
#     ):
#         print(event)

#     print('done..')

# # This runs the async function properly
# if __name__ == "__main__":
#     result = asyncio.run(main())
#     # print(f"Response: {result}")








import asyncio
from typing import Any
from client.llm_client2 import LLMClient
import click

class CLI:
    def __init__(self):
        pass
    def run_single(self):
         pass



async def run(message:dict[str,Any]):
     client = LLMClient()
     async for event in client.chat_completion(
      message,
        True
    ):
             print(event)


@click.command()
@click.argument("prompt",required=False)
async def main():
    messages=[
            {"role":"user","content":"Hello, how are you?"  }
        ]
    asyncio.run(run(messages))
    print('done..')

# This runs the async function properly
if __name__ == "__main__":
    result = asyncio.run(main())
    # print(f"Response: {result}")