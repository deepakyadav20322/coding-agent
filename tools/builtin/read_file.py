
from pydantic import BaseModel,Field
from tools.base import Tool, ToolInvocation, ToolResult, Toolkind
from utils.paths import is_binary_file, resolve_path

class ReadFileParmas(BaseModel):

    path:str = Field(...,description = "Pathe to the file to read (relative to the current working directory or absolute)")

    offset:int = Field(1,ge=1,description="Line number to start reading from (1-based index). Default to 1")

    limit:int|None = Field(None,ge=1,description = "maximum number of lines to read. If not spesified it will read entire file")

class ReadFileTool(Tool):
    name="read_file",
    description=("Read the content of text file. Returns the content with line number. "
                 "For large files us offset and limit to read specific portions. "
                 "Cannot read binary files (images, executables, etc.)."
                 
                 )
    kind= Toolkind.READ

    schema= ReadFileParmas

    MAX_FILE_SIZE = 1024*1024*10  # 10MB

    async def excute(self,invocation:ToolInvocation)->ToolResult:
        params = ReadFileParmas(**invocation.params)
        path   = resolve_path(invocation.cwd,params.path) 

        if not path.exists():
            return ToolResult.error_result(f"File not found:{path}")

        # If the given path is not a file that is like drectory or somethongs else then 
        if not path.is_file():
            return ToolResult.error_result(f"Path is not a file : {path}")
        
        file_size = path.stat().st_size
        
        if file_size > self.MAX_FILE_SIZE:
            return ToolResult.error_result(F"File is too large ({file_size/(1024*1024):.1f}MB)"
                                           f"Maximu is {self.MAX_FILE_SIZE/(1024*1024):.0f}"
                                           )
        if is_binary_file(path):
             file_size_mb = file_size / (1024*1024)
             size_str = f"{file_size_mb:.2f}MB" if file_size_mb>=1 else f"{file_size} bytes"
             return ToolResult.error_result(F"Can not read binary file: {path.name} ({size_str})"
                                           f"This tool omly reads text file"

             )
