# This is used for mange the entire dictionary of tool {you can register tool, unregister tool or register/unregister MCP tool}
# Her we liated out all of our tools in openai spec or schema format

# 💀 Logger is used here because of to see if any error or problrm occers {If you want then you can extend with TUI}


from pathlib import Path
from typing import Any, List
from tools.base import Tool, ToolInvocation, ToolResult

import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self._tools:dict[str,Tool] = {}   # default value is empty dictonary

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
    

    # Get all resiterd tool
    def get_tools(self):
        tools :list[Tool] = []

        for tool in self._tools.values():
            tools.append(tool)
        
        return tools

    
    # This function print open spec formates schema of tools 
    def get_schemas(self)->List[dict[str,Any]]:
        return[tool.to_openai_schema() for tool in self.get_tools()]
    

    # It is a wrapper on extute of abstract base class of Tool
    async def invoke(self, name:str,params:dict[str,Any], cwd:Path | None):
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
            await tool.execute(invocation)
        except Exception as e:
            logger.exception(f"Tool{name} raised unexpected error")
            return ToolResult.error_result(
                f"Internal error : {str(e)}",
                metadata={
                    "tool_name":name
                }
            )

            

