"""Create the interpreters the holdout environment incidents switch between (network once).

np1: NumPy 1.26 + pandas 2.2   np2: NumPy 2.x + pandas 2.x   pd3: NumPy 2.x + pandas 3.x
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "np1": ["numpy==1.26.4", "pandas==2.2.3"],
    "np2": ["numpy>=2.1,<3", "pandas>=2.2,<3"],
    "pd3": ["numpy>=2.1,<3", "pandas>=3,<4"],
}


def main() -> None:
    for name, requirements in PINS.items():
        target = HERE / "envs" / name
        if not (target / "bin" / "python").exists():
            subprocess.run([sys.executable, "-m", "venv", str(target)], check=True)
        python = str(target / "bin" / "python")
        subprocess.run([python, "-m", "pip", "install", "-q", *requirements], check=True)
        versions = subprocess.run(
            [python, "-c", "import numpy, pandas; print(numpy.__version__, pandas.__version__)"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        print(f"{name}: numpy/pandas {versions}")


if __name__ == "__main__":
    main()
