"""Create the matched historical runtimes and record exactly what was installed.

Each good/bad pair uses the same Python (3.11) and the same pinned shared dependencies, so
the only package that differs is the library whose historical transition is studied. The
installed package sets are written to ``ENVIRONMENTS.lock.json`` and checked: a pair whose
freezes differ in anything but the studied package is rejected.

    python3.11 benchmarks/historical/setup_envs.py            # create missing envs, write lock
    python3.11 benchmarks/historical/setup_envs.py --check    # verify existing envs against the lock
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENVS = ROOT / "envs"
LOCK = ROOT / "ENVIRONMENTS.lock.json"

# shared constraints per family; the studied package is the only thing that varies
NUMPY1 = ["numpy==1.26.4", "python-dateutil==2.9.0.post0", "pytz==2025.2", "tzdata==2025.2", "six==1.17.0"]
PANDAS3_ERA = [
    "numpy==2.2.6",
    "pyarrow==21.0.0",
    "python-dateutil==2.9.0.post0",
    "pytz==2025.2",
    "tzdata==2025.2",
    "six==1.17.0",
]
SKLEARN_OLD = ["numpy==2.1.3", "scipy==1.14.1", "joblib==1.4.2", "threadpoolctl==3.5.0"]
# scikit-learn 1.9 added narwhals as a runtime dependency; the shared set is the union of both
# sides' dependencies, so 1.7.2 and 1.8.0 get it too (unused by them), as pytz stays with pandas 3
SKLEARN_NEW = ["numpy==2.3.4", "scipy==1.16.2", "joblib==1.5.2", "threadpoolctl==3.6.0", "narwhals==2.27.1"]

ENVIRONMENTS: dict[str, tuple[str, list[str]]] = {
    "pandas-2.1.4": ("pandas==2.1.4", NUMPY1),
    "pandas-2.2.1": ("pandas==2.2.1", NUMPY1),
    "pandas-2.3.1": ("pandas==2.3.1", PANDAS3_ERA),
    "pandas-2.3.3": ("pandas==2.3.3", PANDAS3_ERA),
    "pandas-3.0.0rc0": ("pandas==3.0.0rc0", PANDAS3_ERA),
    "pandas-3.0.0": ("pandas==3.0.0", PANDAS3_ERA),
    "pandas-3.0.2": ("pandas==3.0.2", PANDAS3_ERA),
    "sklearn-1.5.2": ("scikit-learn==1.5.2", SKLEARN_OLD),
    "sklearn-1.6.0": ("scikit-learn==1.6.0", SKLEARN_OLD),
    "sklearn-1.7.2": ("scikit-learn==1.7.2", SKLEARN_NEW),
    "sklearn-1.8.0": ("scikit-learn==1.8.0", SKLEARN_NEW),
    "sklearn-1.9.0": ("scikit-learn==1.9.0", SKLEARN_NEW),
    # Pillow has no runtime dependencies; these two pre-date this script and are locked here too
    "pillow9": ("pillow==9.5.0", []),
    "pillow10": ("pillow==10.0.0", []),
}
PAIRS = {  # good env, bad env, studied distribution name
    "pandas-2.1.4->2.2.1": ("pandas-2.1.4", "pandas-2.2.1", "pandas"),
    "pandas-2.3.3->3.0.0": ("pandas-2.3.3", "pandas-3.0.0", "pandas"),
    "pandas-2.3.3->3.0.0rc0": ("pandas-2.3.3", "pandas-3.0.0rc0", "pandas"),
    "pandas-2.3.3->3.0.2": ("pandas-2.3.3", "pandas-3.0.2", "pandas"),
    "pandas-2.3.1->3.0.0": ("pandas-2.3.1", "pandas-3.0.0", "pandas"),
    "sklearn-1.5.2->1.6.0": ("sklearn-1.5.2", "sklearn-1.6.0", "scikit-learn"),
    "sklearn-1.7.2->1.8.0": ("sklearn-1.7.2", "sklearn-1.8.0", "scikit-learn"),
    "sklearn-1.8.0->1.9.0": ("sklearn-1.8.0", "sklearn-1.9.0", "scikit-learn"),
    "pillow-9.5.0->10.0.0": ("pillow9", "pillow10", "pillow"),
}


def python_of(name: str) -> Path:
    return ENVS / name / "bin" / "python"


def freeze(name: str) -> dict[str, str]:
    out = subprocess.run(
        [str(python_of(name)), "-m", "pip", "freeze", "--all"], check=True, capture_output=True, text=True
    ).stdout
    packages = {}
    for line in out.splitlines():
        if "==" in line:
            package, version = line.split("==", 1)
            packages[package.lower().replace("_", "-")] = version
    for tool in ("pip", "setuptools", "wheel"):
        packages.pop(tool, None)
    return packages


def create(name: str) -> None:
    target, shared = ENVIRONMENTS[name]
    if not python_of(name).exists():
        subprocess.run([sys.executable, "-m", "venv", str(ENVS / name)], check=True)
    subprocess.run(
        [str(python_of(name)), "-m", "pip", "install", "-q", "--only-binary=:all:", target, *shared],
        check=True,
    )


def lock_entry(name: str) -> dict[str, object]:
    version = subprocess.run(
        [str(python_of(name)), "-c", "import platform; print(platform.python_version())"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "python": version,
        "requested": [ENVIRONMENTS[name][0], *ENVIRONMENTS[name][1]],
        "packages": freeze(name),
    }


def broken(name: str) -> str | None:
    """``pip check`` output when installed requirements are inconsistent, else None."""
    out = subprocess.run([str(python_of(name)), "-m", "pip", "check"], capture_output=True, text=True)
    return None if out.returncode == 0 else out.stdout.strip()


def check_pairs(lock: dict[str, dict[str, object]]) -> list[str]:
    problems = []
    for pair, (good, bad, studied) in PAIRS.items():
        if good not in lock or bad not in lock:
            continue
        g, b = lock[good]["packages"], lock[bad]["packages"]
        assert isinstance(g, dict) and isinstance(b, dict)
        differing = sorted(k for k in set(g) | set(b) if g.get(k) != b.get(k))
        if lock[good]["python"] != lock[bad]["python"]:
            problems.append(f"{pair}: python differs")
        if differing != [studied]:
            problems.append(f"{pair}: packages differing beyond {studied}: {differing}")
    return problems


def main() -> int:
    check_only = "--check" in sys.argv
    selected = [a for a in sys.argv[1:] if not a.startswith("--")] or list(ENVIRONMENTS)
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    for name in selected:
        if not check_only:
            create(name)
            print(f"ready: {name}", flush=True)
        damaged = broken(name)
        if damaged:
            print(f"BROKEN: {name}: {damaged}")
            return 1
        current = lock_entry(name)
        if check_only and lock.get(name) != current:
            print(f"MISMATCH: {name} differs from the lock")
            return 1
        lock[name] = current
    problems = check_pairs(lock)
    for problem in problems:
        print("PAIR PROBLEM:", problem)
    if not check_only:
        LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(lock)} environments locked; {len(PAIRS)} pairs checked; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
