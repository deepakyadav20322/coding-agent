



from dataclasses import Field
import json

from pydantic import BaseModel

from config.loader import get_data_directory
from tools.base import Tool, ToolInvocation, ToolResult, Toolkind


class MemoryParams(BaseModel):
    action:str = Field(...,description="Action: 'set', 'get', 'delete', 'list', 'clear'")
    key:str| None = Field(None, description="Memory key: (required for `set`, `get`, `delete` actions)")
    value:str | None = Field(None, description = "Value to store (required for `set` action)")
    
    
class MemoryTool(Tool):
    name = "memory"
    description = "Store and retrieve persistent memory. Use this to remember user preferences important context or notes."
    kind = Toolkind.MEMORY
    schema = MemoryParams

    def _load_memory(self)->dict:
        data_dir = get_data_directory()
        data_dir.mkdir(parents=True, exist_ok = True)
        path =  data_dir / "user_memory.json"

        # If path does not exits then it return empty entries dict if exsits then it return key value pair in entries.
        if not path.exists():
            return {"entries":{} }
        
        try:
            content  = path.read_text(encoding="utf-8")
            data = json.loads(content)
            return data
        except Exception:
            # if nay sort or error in file read then return empty entries dict or josn
            return {"entries":{}}
    
    def _save_memory(self,memory:dict)->None:
        data_dir = get_data_directory()
        data_dir.mkdir(parents=True, exist_ok = True)
        path =  data_dir / "user_memory.json"

        path.write_text(json.dumps(memory,indent=2,ensure_ascii=False))



    async def execute(self,invocation:ToolInvocation)->ToolResult:
        params = MemoryParams(**invocation.params)

        if params.action == "set":
            if not params.key or not params.value:
                return ToolResult.error_result("`Key` and `Value` are required for 'set' action")
            # load memory
            memory = self._load_memory()
            # updated the memory
            memory["entries"][params.key] = params.value
            #how memory object looks in file = >>>  {"enstries":{key:"value"}}

            # noe save the updated memory back to file
            self._save_memory(memory)

            return ToolResult.success_result(
                f"Set memory: {params.key}"
            )
