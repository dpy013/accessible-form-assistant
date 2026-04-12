import os
import sys
from pathlib import Path

env = Environment(ENV=os.environ)
root = Path(__file__).resolve().parent
python = sys.executable

if not os.environ.get("VIRTUAL_ENV"):
    Exit("Please activate the uv virtual environment before running scons.")

check = env.Command(
    "check",
    [],
    f'"{python}" -m compileall "{root / "src"}"',
)

package = env.Command(
    "package",
    [],
    f'"{python}" -m build "{root}"',
)

Default(check)
