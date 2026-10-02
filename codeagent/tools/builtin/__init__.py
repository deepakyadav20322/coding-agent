from codeagent.tools.builtin.edit_file import EditFileTool
from codeagent.tools.builtin.glob import GlobTool
from codeagent.tools.builtin.grep import GrepTool
from codeagent.tools.builtin.list_dir import ListDirTool
from codeagent.tools.builtin.memory import MemoryTool
from codeagent.tools.builtin.read_file import ReadFileTool
from codeagent.tools.builtin.shell import ShellTool
from codeagent.tools.builtin.todo import TodosTool
from codeagent.tools.builtin.web_fetch import WebFetchTool
from codeagent.tools.builtin.web_search import WebSearchTool
from codeagent.tools.builtin.write_file import WriteFileTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
     "GlobTool",
     "WebSearchTool",
    "WebFetchTool",
    "TodosTool",
    "MemoryTool",
    

]

def get_all_builtin_tools()->list[type]:
    return[
        ReadFileTool,
        WriteFileTool,
        EditFileTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool,
    ]
