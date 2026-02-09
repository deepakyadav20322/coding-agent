

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
from agent.agent import Agent
from agent.events import AgentEventType
from client.llm_client2 import LLMClient
import click

class CLI:
    def __init__(self):
        self.agent = Agent | None = None
    async def run_single(self,message:str):
         async with Agent() as agent:
             self.agent = agent
             self._process_message(message)

    # This function is responsible for processing the user message and getting the response from the agent and print it to the according to the type of event and message type we get from the agent
    async def _process_message(self,message:str)->str | None:
        if not self.agent:
            return None
        async for event in self.run_single(message):
            if event.type == AgentEventType.AGENT_START:
                # print(f"Agent started with message: {event.data.get('message')}")
                return
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content","")





# We remove it from here and put it into agent.py
# async def run(message:dict[str,Any]):
#      client = LLMClient()
#      async for event in client.chat_completion(
#       message,
#         True
#     ):
#              print(event)


@click.command()
@click.argument("prompt",required=False)
async def main(prompt:str|None):
    cli = CLI()
    # messages=[
    #         {"role":"user","content":prompt}
    #     ]
    asyncio.run(cli.run_single(prompt))

# This runs the async function properly
if __name__ == "__main__":
    result = asyncio.run(main())
    # print(f"Response: {result}")