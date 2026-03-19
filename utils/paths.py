
from pathlib import Path


def resolve_path(base: str | Path , path:str|Path):
    path = Path(path)

    if path.is_absolute():
        return path.resolve()
    
    return Path(base).resolve() / path

def display_path_rel_to_cwd(path:str,cwd:Path|None)->str:
    try:
        p = Path(path)

    except:
        return path
    
    if cwd:
        try:
            return str(p.relative_to(cwd))
        except:
            pass
    return(p)


def ensure_parent_directory(path :str | Path)->Path:
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    return path


# here we take first 8 bytes and check null if get then binary (If wnat then can make complicated and thraw to it)
def is_binary_file(path:str | Path) -> bool:
    try:
        with open(path,"rb") as f:
            chunk = f.read(8129)
            return b"\x00" in chunk
    except(OSError,IOError):
        return False