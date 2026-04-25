# This is used for mange the entire dictionary of tool {you can register tool, unregister tool or register/unregister MCP tool}
# Her we liated out all of our tools in openai spec or schema format

# 💀 Logger is used here because of to see if any error or problrm occers {If you want then you can extend with TUI}


from os import name
from pathlib import Path
from typing import Any, List
from config.config import Config
from tools.base import Tool, ToolInvocation, ToolResult
from tools.builtin import ReadFileTool, get_all_builtin_tools
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self,config: Config):
        self._tools:dict[str,Tool] = {}   # default value is empty dictonary
        self.config = config

    def register(self,tool:Tool)->None:
        if tool.name in self._tools:
            logger.warning(f"Overwriting exiting tool: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool {tool.name}")


    def unregister(self,name)->bool:
        if name in self._tools:
            del self._tools[name]
            return True
        
        return False
    
    def get(self, name: str) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        elif name in self._mcp_tools:
            return self._mcp_tools[name]

        return None

    # Get all resiterd tool
    def get_tools(self):
        tools :list[Tool] = []

        for tool in self._tools.values():
            tools.append(tool)
        
        return tools

    
    # This function print open spec formates schema of tools 
    def get_schemas(self)->List[dict[str,Any]]:
        return[tool.to_openai_schema() for tool in self.get_tools()]
    

    # It is a wrapper on extute of abstract base class of Tool {it combine validate and execute in one function work as wrapper on execute function of tool}
    async def invoke(self, name:str,params:dict[str,Any], cwd:Path)->ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult.error_result(
                f"Unknown tool {name}",
                metaData={"tool_name":name},
            )
        
        # when tools call then it definatly have it's requred parameter I am here validate those before actual invoking/excuting work and validate params return list of string if validations fail other wise empty list.
        validatoin_errors = tool.validate_params(params)
        
        if validatoin_errors:
            return ToolResult.error_result(
                f"invalid parameters: {';'.join(validatoin_errors)}",
                metadata={
                    "tool_name":name,
                    "validation_error":validatoin_errors
                }
            )
        invocation = ToolInvocation(
            params=params,
            cwd=cwd
        )
        try:
           result  = await tool.execute(invocation)
            # catch a broder exception that our app don't fail
        except Exception as e:
            logger.exception(f"Tool{name} raised unexpected error")
            result =  ToolResult.error_result(
                f"Internal error : {str(e)}",
                metadata={
                    "tool_name":name
                }
            )
        return result

# This is a global function which used to create an global funtion form where we register all tools (It is like singleton instance)
def create_default_registry(config: Config)->ToolRegistry:
    registry = ToolRegistry(config)

    for tool_class in get_all_builtin_tools():
        registry.register(tool_class(config))

    return registry
            

# 04:01:00