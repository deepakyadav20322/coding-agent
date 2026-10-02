

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
import os
from pathlib import Path
import sys
from typing import Any
from codeagent.agent.agent import Agent
from codeagent.agent.events import AgentEventType
from codeagent.client.llm_client2 import LLMClient
import click

from codeagent.config.config import Config
from codeagent.config.loader import (
    load_config,
    load_system_config_raw,    # NEW
    save_system_config,        # NEW
    get_system_config_path,    # NEW
    _get_project_config,       # NEW
)
from codeagent.ui.slash_command import handle_slash_command, is_slash_command
from codeagent.ui.tui import TUI, get_console


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

    def __init__(self,config: Config):
        self.agent: Agent | None = None
        self.config = config
        self.tui = TUI(config,console)

    async def run_single(self, message: str) -> None:
 
        async with Agent(config=self.config) as agent:

            self.agent = agent

            return await self._process_message(message)

    # This is used to run in interactive mode {by communicating with or cli }
    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            "AI Agent",
            lines=[
                # f"model: openrouter/free",
                f"model: {self.config.model_name}",
                # f"model: nvidia/nemotron-3-nano-30b-a3b:free",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )

        async with Agent(config=self.config) as agent:

            self.agent = agent
            while True: # It is infinite loop to intract in cli 
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue

                    # Slash commands are handled locally -- they never reach
                    # the LLM. Anything else is treated as a normal prompt.
                    if is_slash_command(user_input):
                        result = handle_slash_command(user_input, self.config, console)
                        if result == "exit":
                            break
                        continue

                    await self._process_message(user_input)

                except KeyboardInterrupt:
                    console.print("\n[dim]Use /exit to quit[/dim]")
                except EOFError:
                    break
                except Exception as e:
                    # Never let one bad turn kill the whole session.
                    self.tui.show_error(f"{type(e).__name__}: {e}", title="Unexpected error")


        return console.print("\n[dim]Good bye![/dim]")
            
            

            

    def _get_tool_kind(self, tool_name: str) -> str | None:
        tool_kind = None
        tool = self.agent.session.tool_registry.get(tool_name)
        if not tool:
            # tool_kind = None
            return None

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

            # elif event.type == AgentEventType.AGENT_ERROR:
            #     error = event.data.get("error", "Unknown error")
            #     console.print(f"\n[error]ERROR: {error}[/error]")

            elif event.type == AgentEventType.AGENT_ERROR:
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
                self.tui.show_error(event.data.get("error", "Unknown error"))

            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name =  event.data.get("name","unknown")
                # tool_kind = None
                # # tool = self.agent.tool_registry.get(tool_name)
                # tool = self.agent.session.tool_registry.get(tool_name)
                # # print(type(self.agent.session.tool_registry))
                # if not toosl:
                #     tool_kind = None
                
                tool_kind = self._get_tool_kind(tool_name)
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
                    event.data.get('diff'),
                \
                    event.data.get("truncated", False),
                    event.data.get("exit_code")
                   
                )

                
                
        return final_response 

            

# ============================================================================
# CLI ENTRY POINT
# ============================================================================
# This used to be a single @click.command. We're upgrading to a @click.group
# so we can have subcommands:
#   codeagent              -> runs the agent (default = interactive)
#   codeagent run "..."    -> one-shot prompt
#   codeagent login        -> save API key to system config
#   codeagent config show  -> show where configs live and what's set
# ============================================================================


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context):
    """codeagent - a local coding agent CLI.

    Run with no arguments to start an interactive session.
    Use `codeagent run "your prompt"` for one-shot mode.
    """
    # If no subcommand was given, default to running the agent.
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@main.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
def run(prompt: str | None, cwd: Path | None):
    """Run the agent (interactive if no prompt given)."""
    try:
        config = load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)

    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)
    #  # ===== TEMPORARY DEBUG: print the system prompt so we can verify =====
    # # the environment block is being injected. Delete this block once
    # # you've confirmed the prompt looks right.
    # from prompts.system import get_system_prompt
    # print("=" * 70)
    # print("SYSTEM PROMPT (debug):")
    # print("=" * 70)
    # print(get_system_prompt(config))
    # print("=" * 70)
    # # ==============================================

    cli = CLI(config=config)
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


# `codeagent login` - prompts for API key + base URL, saves to system config.
# After this, the user never has to `set API_KEY=...` again.
@main.command()
@click.option(
    "--base-url",
    default="https://openrouter.ai/api/v1",
    show_default=True,
    help="LLM provider base URL.",
)
def login(base_url: str):
    """Save API key and base URL to your system config file."""
    # hide_input=True means the key won't show on screen as it's typed
    api_key = click.prompt("API key", hide_input=True, confirmation_prompt=False)

    if not api_key.strip():
        console.print("[error]Empty key. Aborting.[/error]")
        sys.exit(1)

    # Read existing config so we don't lose other settings (model, etc.)
    data = load_system_config_raw()
    data["api_key"] = api_key.strip()
    data["base_url"] = base_url.strip()

    path = save_system_config(data)
    console.print(f"[success]Saved to:[/success] {path}")
    console.print("[dim]You can now run `codeagent` from any folder.[/dim]")

     # An API_KEY env var takes priority over the saved key, so an old expired
    # key in the environment would keep being used. Warn about it.
    if os.environ.get("API_KEY"):
        console.print(
            "\n[warning]Warning: the API_KEY environment variable is set and overrides "
            "the key you just saved.[/warning]\n"
            "Remove it:\n"
            "  Windows (current terminal):  set API_KEY=\n"
            "  Windows (permanently):       setx API_KEY \"\"   then open a new terminal\n"
            "  macOS / Linux:               unset API_KEY"
        )


# `codeagent config show` - prints config file locations and current values.
# Masks most of the API key so it doesn't get exposed accidentally.
@main.group()
def config():
    """Manage codeagent configuration."""
    pass


@config.command("show")
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
def config_show(cwd: Path | None):
    """Show config file locations and current effective settings."""
    system_path = get_system_config_path()
    project_path = _get_project_config(cwd or Path.cwd())

    console.print(f"[bold]System config:[/bold] {system_path}")
    console.print(f"  exists: {system_path.is_file()}")
    console.print(f"[bold]Project config:[/bold] {project_path or '(none)'}")

    try:
        cfg = load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Could not load config: {e}[/error]")
        return

    # Mask the API key so only the first 4 and last 4 chars show.
    key = cfg.api_key
    masked = (key[:4] + "..." + key[-4:]) if key and len(key) > 8 else "(not set)"
    console.print(f"[bold]api_key:[/bold]   {masked}")
    console.print(f"[bold]base_url:[/bold]  {cfg.base_url or '(not set)'}")
    console.print(f"[bold]model:[/bold]     {cfg.model_name}")


if __name__ == "__main__":
    main()




# FOR WINDOWS [it diff for mac/linux] {system level config.tomel file where required config defined}
# "C:\Users\DEEPAK YADAV\AppData\Local\claude-code-type-agent\claude-code-type-agent\config.toml"



#  HOW TO RUN 
# set API_KEY=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
# set BASE_URL => set BASE_URL=https://openrouter.ai/api/v1  {iF NEED OTHER WISE IT TAKE IT FROM TOMAL FILE SYSTEM OR PROJECT LEVEL}





    # 06:11:00 timing
    # 07:41:00 max_turn used ehich define in session
    # 09:05:29 