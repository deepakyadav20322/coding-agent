# Start shell built in tool call 


from tools.base import Toolkind


class ShellTool:
    name = "shell"
    kind = Toolkind.SHELL
    description = "Execute a shell command. Use this for running system commands, scripts and CLI tools."