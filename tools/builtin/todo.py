

import uuid

from pydantic import BaseModel, Field

from config.config import Config
from tools.base import Tool, ToolInvocation, ToolResult, Toolkind

class TodosParams(BaseModel):
    action:str = Field(...,description="Action: 'add' , 'complete', 'list', 'clear' ")
    id:str|None = Field(None,description="Todo ID (for complete)")
    content:str|None = Field(None,description="Todo content (for add)")



class TodosTool(Tool):
    name="todos"
    description = "Manage a task list for current session. Use this to track progress on multistep tasks."
    kind =Toolkind.MEMORY
    schema = TodosParams

    def __init__(self, config:Config)->None:
        super().__init__(config)
        self._todos: dict[str,str] = {}


    async def execute(self, invocation:ToolInvocation):
        params = TodosParams(**invocation.params)

        
        if params.action.lower() =="add":
            if not params.content:
                return ToolResult.error_result("Content required for add action")
            todo_id = str(uuid.uuid4())[:8]
            self._todos[todo_id] = params.content
            return ToolResult.success_result(f"Added todos [{todo_id}]:{params.content}")
        
        elif params.action.lower()=="complete":
            if not params.id:
                return ToolResult.error_result(" `id` required for `complete` action")
            if params.id  not in self._todos:
                return ToolResult.error_result("Todos not found: {params.id}")
            content = self._todos.pop(params.id)
            return ToolResult.success_result(f"Complete todo [{params.id}]: {content}")
        elif params.action.lower() == "list":
            if not self._todos:
                return ToolResult.error_result("No todos")
            lines = ['Todos:']
            for todo_id ,content in self._todos.items():
                 lines.append(f"   [{todo_id}] {content}")
            ToolResult.success_result("\n".join(lines))
        elif params.action.lower() =="clear":
            count = len(self._todos)
            self._todos.clear()
            return ToolResult.success_result(f"Clear {count} todos ")
        else:
            return ToolResult.success_result(f"Unknown action: {params.action}")