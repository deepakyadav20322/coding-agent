# Start shell built in tool call 


from tools.base import ToolConfirmation, ToolInvocation, ToolResult, Toolkind
from pydantic import BaseModel , Field


BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "fdisk",
    "parted",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777 /",
    "chmod -R 777",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}

class ShellParams(BaseModel):
    command: str = Field(..., description="The shell command to execute")
    timeout:int = Field(
        120,ge=1,le=600, description="Timeout in seconds (default 120)"
    )
    cwd:str| None = Field(None,description="Working directory for the commond")

class ShellTool:
    name = "shell"
    kind = Toolkind.SHELL
    description = "Execute a shell command. Use this for running system commands, scripts and CLI tools."

    schema = ShellParams

    async def execute(self,invocation:ToolInvocation)->ToolResult:

        params = ShellParams(**invocation.params)

        for blocked in BLOCKED_COMMANDS:
            if blocked in params.command:
                return ToolConfirmation(
                    tool_name=self.name,
                    params=invocation.params,
                    description=f"Execute (BLOCKED): {params.command}",
                    command=params.command,
                    is_dangerous=True,
                )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Execute: {params.command}",
            command=params.command,
            is_dangerous=False,
        )
        