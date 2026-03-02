

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
from pathlib import Path
import sys
from typing import Any
from agent.agent import Agent
from agent.events import AgentEventType
from client.llm_client2 import LLMClient
import click

from ui.tui import TUI, get_console


console = get_console()

# class CLI:
#     def __init__(self):
#         self.agent: Agent | None = None
#         self.tui = TUI(console=console)

#     async def run_single(self,message:str)->str|None:
#          async with Agent() as agent:
#              self.agent = agent
#              return  await self._process_message(message)

#     # This function is responsible for processing the user message and getting the response from the agent and print it to the according to the type of event and message type we get from the agent
#     async def _process_message(self,message:str)->str | None:
#         if not self.agent:
#             return None
#         async for event in self.agent.run(message):
#             if event.type == AgentEventType.AGENT_START:
#                 # print(f"Agent started with message: {event.data.get('message')}")

#                 continue
#             if event.type == AgentEventType.TEXT_DELTA:
#                 content = event.data.get("content","")
#                 self.tui.stream_assistant_delta(content)
class CLI:

    def __init__(self):
        self.agent: Agent | None = None
        self.tui = TUI(console=console)

    async def run_single(self, message: str) -> None:

        async with Agent() as agent:

            self.agent = agent

            await self._process_message(message)

    # This is used to run in interactive mode {by communicating with or cli }
    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "AI Agent",
            lines=[
                f"model: openrouter/free",
                # f"model: nvidia/nemotron-3-nano-30b-a3b:free",
                f"cwd: {Path.cwd()}",
                "commands: /help /config /approval /model /exit",
            ],
        )

        async with Agent() as agent:

            self.agent = agent
            while True: # It is infinite loop to intract in cli 
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue
                    await self._process_message(user_input)

                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit[/dim]")
                except EOFError:
                    break

        return console.print("\n[dim]Good buy![/dim]")
            
            

            

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool_kind = None
        tool = self.agent.tool_registry.get(tool_name)
        if not tool:
            tool_kind = None

        tool_kind = tool.kind.value

        return tool_kind

    
    async def _process_message(self, message: str) -> None:

        if not self.agent:
            return
        
        # It(assistant_streaming) is used to show assistance start horizontal line before first message coming 
        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            # print(event)

            # ❌ DO NOT EXIT HERE
            if event.type == AgentEventType.AGENT_START:
                continue

            if event.type == AgentEventType.TEXT_DELTA:

                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False

            # if event.type == AgentEventType.AGENT_END:
            #     self.tui.stream_assistant_delta("\n")
            #     break

            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]ERROR: {error}[/error]")
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name =  event.data.get("name","unknown")
                tool_kind = None
                tool = self.agent.tool_registry.get(tool_name)
                if not tool:
                    tool_kind = None
                
                tool_kind = tool.kind.value
                self.tui.tool_call_start(
                    event.data.get("call_id",""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments",{}),

                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                \
                    event.data.get("truncated", False),
                   
                )

                
                
        return final_response 

            


@click.command()
@click.argument("prompt",required=False)
def main(prompt:str|None):
    cli = CLI()
    # messages=[
    #         {"role":"user","content":prompt}
    #     ]
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
                sys.exit(1)
    else:
         asyncio.run(cli.run_interactive());
# This runs the async function properly
main()
    # print(f"Response: {result}")










    # 06:11:00 timing