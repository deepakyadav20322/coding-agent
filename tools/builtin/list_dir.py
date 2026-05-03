from tools.base import Tool, ToolKind
from pydantic import BaseModel, Field



class ListDirParams(BaseModel):
    path: str = Field(
        ".", description="Directory path to list (default: current directory)"
    )
    include_hidden: bool = Field(
        False,
        description="Whether to include hidden files and directories (default: false",
    )


class ListDirTool(Tool):
    name = "list_dir"
    description = "List contents of a directory"
    kind = ToolKind.READ
    schema = ListDirParams