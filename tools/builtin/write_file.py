from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolResult , Toolkind
from utils.paths import resolve_path



class WriteFileParams(BaseModel):
    path = str = Field(
        ...,
        description="Path to the file to write (relative to working directory or absolute)"
    )
    content = str= Field(..., description="Content to write to the file")
    create_directories:bool = Field(
        True,
        description="Create parent directories if they don't exist"
    )

class WriteFileTool(Tool):
    name= 'write_file'

    # I write decription like that it not work like edit file {we add words that give  difference to llm }
    description = (
        "Write content to a file. Creates the file if it doesn't exist, "
        "or overwrites if it does. Parent directories are created automatically. "
        "Use this for creating new files or completely replacing file contents. "
        "For partial modifications, use the edit tool instead."
    )
    kind = Toolkind.WRITE
    schema= WriteFileParams

    async def execute(self, invocation:ToolInvocation)->ToolResult:
        params = WriteFileParams(**invocation.params)
        # invocation.cwd => whatever we are write now working directory
        # params.path => what is llm is telling us to write to (it can be relative or absolute path)
        # path => now we get absolute or relative path after resolve_path call
        path = resolve_path(invocation.cwd, params.path)

        is_new_file= not path.exists()

        # 07:52:40 --------->