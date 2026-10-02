

"""
One-time migration: move the flat layout into a single `codeagent/` package.
Run from the project root (the folder that contains pyproject.toml).
"""
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path.cwd()
PKG = ROOT / "codeagent"
SUBPACKAGES = ["agent", "client", "config", "context", "prompts", "tools", "ui", "utils"]
MODULES = ["main.py"]

if not (ROOT / "pyproject.toml").is_file():
    raise SystemExit("Run this from the project root (where pyproject.toml is).")
if PKG.exists():
    raise SystemExit("codeagent/ already exists - migration was already done.")

PKG.mkdir()
(PKG / "__init__.py").write_text('__version__ = "0.4.0"\n', encoding="utf-8")
(PKG / "__main__.py").write_text(
    "from codeagent.main import main\n\nif __name__ == \"__main__\":\n    main()\n",
    encoding="utf-8",
)

# 1) Move folders/files. Use `git mv` when possible so history is kept.
use_git = (ROOT / ".git").exists() and shutil.which("git")
for name in SUBPACKAGES + MODULES:
    src = ROOT / name
    if not src.exists():
        print(f"skip (not found): {name}")
        continue
    if use_git:
        subprocess.run(["git", "mv", name, f"codeagent/{name}"], check=True)
    else:
        shutil.move(str(src), str(PKG / name))
    print(f"moved {name} -> codeagent/{name}")

# 2) Every folder inside codeagent/ becomes a real package.
for folder in [p for p in PKG.rglob("*") if p.is_dir() and p.name != "__pycache__"]:
    init = folder / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")

# 3) Rewrite imports:  `from config.x import y` -> `from codeagent.config.x import y`
names = "|".join(SUBPACKAGES + ["main"])
pattern = re.compile(rf"^(\s*)(from|import)\s+({names})(?=[\s.])", re.MULTILINE)
for py in PKG.rglob("*.py"):
    text = py.read_text(encoding="utf-8")
    new = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)} codeagent.{m.group(3)}", text)
    if new != text:
        py.write_text(new, encoding="utf-8")
        print(f"rewrote imports in {py.relative_to(ROOT)}")

# 4) Remove stale build output so old flat-layout files can't sneak into the wheel.
for junk in ["build", "dist", "codeagent_cli.egg-info"]:
    shutil.rmtree(ROOT / junk, ignore_errors=True)

print("\nDone. Now update pyproject.toml and run: pip install -e .")


