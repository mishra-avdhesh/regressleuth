"""Create the two interpreters the environment demo switches between (needs network once).

envs/pandas2 holds pandas 2.x and envs/pandas3 holds pandas 3.x; both also get numpy.
Nothing else is installed, so the only difference between them is the pandas major version.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {"pandas2": "pandas>=2.2,<3", "pandas3": "pandas>=3,<4"}


def main() -> None:
    for name, requirement in PINS.items():
        target = HERE / "envs" / name
        if not (target / "bin" / "python").exists():
            subprocess.run([sys.executable, "-m", "venv", str(target)], check=True)
        python = target / "bin" / "python"
        subprocess.run([str(python), "-m", "pip", "install", "-q", requirement, "numpy"], check=True)
        version = subprocess.run(
            [str(python), "-c", "import pandas; print(pandas.__version__)"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        print(f"{name}: pandas {version}")


if __name__ == "__main__":
    main()
