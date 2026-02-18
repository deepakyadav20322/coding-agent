
from pathlib import Path


def resolve_path(base: str | Path , path:str|Path):
    path = Path(path)

    if path.is_absolute():
        return path.resolve()
    
    return Path(base).resolve() / path

# here we take first 8 bytes and check null if get then binary (If wnat then can make complicated and thraw to it)
def is_binary_file(path:str | Path) -> bool:
    try:
        with open(path,"rb") as f:
            chunk = f.read(8129)
            return f"\x00" in chunk
    except(OSError,IOError):
        return False