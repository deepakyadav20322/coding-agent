
from pydantic import BaseModel,Field
from tools.base import Tool, ToolInvocation, ToolResult, Toolkind
from utils.paths import is_binary_file, resolve_path
from utils.text import count_tokens, truncate_text

class ReadFileParmas(BaseModel):

    path:str = Field(...,description = "Pathe to the file to read (relative to the current working directory or absolute)")

    offset:int = Field(1,ge=1,description="Line number to start reading from (1-based index). Default to 1")

    limit:int|None = Field(None,ge=1,description = "maximum number of lines to read. If not spesified it will read entire file")

class ReadFileTool(Tool):
    name="read_file"
    description=("Read the content of text file. Returns the content with line number. "
                 "For large files us offset and limit to read specific portions. "
                 "Cannot read binary files (images, executables, etc.)."
                 
                 )
    kind= Toolkind.READ

    schema= ReadFileParmas

    MAX_FILE_SIZE = 1024*1024*10  # 10MB
    MAX_OUTPUT_TOKENS = 25000  
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
        
        # Now not a binary fil and not pass above conditions then means that is correct text file now we do reading related stuffs now
        try:
            try:
                content = path.read_text(encoding="utf-8")
            
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")

            lines = content.splitlines()
            total_lines = len(lines)

            if total_lines ==0:
                # if want then can pass empty string because no content but LLm may confused may they think that, Is I do something wrong that's why I get empty string . For this need to send netter output with metadata.
                return ToolResult.success_result(
                    "File is empty",
                    metadata={"lines":0}  
                )
            start_idx = max(0,params.offset - 1) # We are doing -1 because here index strt from 0  but line no start from 1.
            if params.limit is not None :
                end_idx = min(start_idx+params.limit , total_lines)
            else:
                end_idx = total_lines
            
            selected_lines = lines[start_idx:end_idx]

            formatted_lines = []

            for i, line in enumerate(selected_lines,start=start_idx+1):
                formatted_lines.append(f"{i:6}|{line}") # it gives out the index and line

                output = "\n".join(formatted_lines)
                token_counts = count_tokens(output,"nvidia/nemotron-3-nano-30b-a3b:free")

            truncated = False
            if token_counts > self.MAX_OUTPUT_TOKENS:  # In this case we need to truncate the text
                output = truncate_text(
                    output,
                    self.MAX_OUTPUT_TOKENS,
                    suffix="\n... [truncated {total_lines} total lines]",
                    
                )
                trunctaed = True

            metadata_lines  = []
            if start_idx>0 and end_idx < total_lines:
                metadata_lines.append(f"showing Lines {start_idx+1}-{end_idx} of {total_lines}")
            
                if metadata_lines:
                    header = " | ".join(metadata_lines) + "\n\n" # these aew used to show users then do good things
                    output = header + output

                return ToolResult.success_result(
                    output=output,
                    truncated=truncated,
                    metadata={
                        "path": str(path),
                        "total_lines": total_lines,
                        "shown_start": start_idx + 1,
                        "shown_end": end_idx,
                    },
                )
        except Exception as e:
            return ToolResult.error_result(f"Failed to read file: {e}")



