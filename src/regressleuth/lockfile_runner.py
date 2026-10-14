"""Replay one dependency mix of a lockfile incident (the command adapter's runner).

    python -m regressleuth.lockfile_runner --state STATE.json --result RESULT.json

The state names a version, or ``absent``, for every changed distribution. The runner
installs exactly that pin set (``--no-deps``) into a virtual environment cached by pin
set, adds the project (editable, without dependencies) and runs the incident's pytest
node IDs. It writes ``{"metric": 1.0}`` when every node passed, ``{"metric": 0.0}`` when
any failed, errored, was skipped or could not be collected, and
``{"status": "incompatible"}`` when the mix cannot be installed or ``uv pip check``
reports a conflict. Installed files are checked against their wheels' RECORD hashes.
Anything else (no ``uv``, unknown node IDs, a pytest crash) exits non-zero and is
classified by Regressleuth as a replay error. Needs ``uv`` on PATH (``pip install uv``).
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def find_uv() -> str:
    found = os.environ.get("REGRESSLEUTH_UV") or shutil.which("uv")
    if found:
        return found
    import importlib

    try:
        return str(importlib.import_module("uv").find_uv_bin())
    except ImportError:
        raise SystemExit("uv is required for lockfile incidents: pip install uv") from None


def altered_files(venv: Path) -> list[str]:
    """Installed files whose content matches no sha256 that any wheel RECORD lists for them."""
    altered = []
    for site in [*venv.glob("lib/python3*/site-packages"), *venv.glob("Lib/site-packages")]:
        expected: dict[str, set[str]] = {}
        for record in site.glob("*.dist-info/RECORD"):
            for row in csv.reader(record.read_text(encoding="utf-8").splitlines()):
                if len(row) >= 2 and row[1].startswith("sha256=") and not row[0].endswith(".pyc"):
                    expected.setdefault(row[0], set()).add(row[1][7:])
        for name, digests in expected.items():
            path = site / name
            if path.is_file():
                digest = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b"=")
                if digest.decode() not in digests:
                    altered.append(name)
    return altered


def venv_python(venv: Path) -> Path:
    """The interpreter of a virtual environment (``Scripts\\python.exe`` on Windows)."""
    windows = venv / "Scripts" / "python.exe"
    return windows if windows.exists() else venv / "bin" / "python"


def environment_for(cases: dict[str, Any], pins: list[str], root: Path, uv: str) -> tuple[Path, bool, str]:
    """Return (venv, compatible, detail); built once per pin set, safe across processes."""
    project = Path(cases["project"])
    key = hashlib.sha256(
        "\n".join(
            [cases["python"], cases["install_project"], str(cases.get("wheels_only")), str(project), *pins]
        ).encode()
    ).hexdigest()[:24]
    venv = root / key
    root.mkdir(parents=True, exist_ok=True)
    with open(root / f"{key}.lock", "w") as lock:
        try:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX)  # parallel replays of one mix build it once
        except ImportError:  # pragma: no cover - Windows: replays of one mix must not run in parallel
            pass
        marker = venv / "regressleuth-env.json"
        if marker.exists():
            saved = json.loads(marker.read_text(encoding="utf-8"))
            return venv, saved["compatible"], saved["detail"]
        if venv.exists():  # unfinished build from an interrupted run
            shutil.rmtree(venv)

        def run(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([uv, *args], capture_output=True, text=True, check=False)

        created = run("venv", "--quiet", "--python", cases["python"], str(venv))
        if created.returncode:
            raise SystemExit(
                f"could not create a Python {cases['python']} environment: {created.stderr[-800:]}"
            )
        (venv / "pins.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
        python = str(venv_python(venv))
        install = ["pip", "install", "--quiet", "--python", python, "--no-deps", "-r", str(venv / "pins.txt")]
        for url in cases.get("index_urls", []):  # e.g. PyTorch's CPU index; tried before PyPI
            install += ["--extra-index-url", url]
        if cases.get("wheels_only"):
            install += ["--only-binary", ":all:"]
        installed = run(*install)
        compatible, detail = installed.returncode == 0, installed.stderr[-2000:]
        if compatible and cases["install_project"] == "editable":
            added = run("pip", "install", "--quiet", "--python", python, "--no-deps", "-e", str(project))
            if added.returncode:
                raise SystemExit(f"the project itself could not be installed: {added.stderr[-800:]}")
        if compatible:
            tampered = altered_files(venv)
            if tampered:
                raise SystemExit(f"installed files differ from their wheel RECORD hashes: {tampered[:5]}")
            checked = run("pip", "check", "--python", python)
            compatible, detail = checked.returncode == 0, (checked.stdout + checked.stderr)[-2000:]
        marker.write_text(json.dumps({"compatible": compatible, "detail": detail, "pins": pins}, indent=1))
        return venv, compatible, detail


def outcome(cases: dict[str, Any], venv: Path, report: Path) -> float | None:
    """1.0 if every named node passed, 0.0 if not, None for a runner-level failure."""
    completed = subprocess.run(
        [
            str(venv_python(venv)),
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
            *cases.get("pytest_args", []),
            *cases["tests"],
        ],
        cwd=cases["project"],
        env={**os.environ, **{str(k): str(v) for k, v in cases.get("test_environment", {}).items()}},
        capture_output=True,
        text=True,
        timeout=cases.get("test_timeout_seconds", 1800),
        check=False,
    )
    # the report is written by pytest in this process tree, not taken from outside
    nodes = list(ET.parse(report).getroot().iter("testcase")) if report.exists() else []  # noqa: S314
    if any(
        child.tag == "error" and child.get("message") == "collection failure"
        for node in nodes
        for child in node
    ):
        return 0.0  # the test module cannot even be imported under this mix
    if completed.returncode not in (0, 1, 2) or not report.exists():
        sys.stderr.write(completed.stdout[-3000:] + completed.stderr[-3000:])
        return None
    if completed.returncode == 0 and len(nodes) < len(cases["tests"]):
        sys.stderr.write(f"expected {len(cases['tests'])} tests, pytest ran {len(nodes)}\n")
        return None
    failed = any(child.tag in {"failure", "error", "skipped"} for node in nodes for child in node)
    return 1.0 if completed.returncode == 0 and not failed else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m regressleuth.lockfile_runner")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args(argv)
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases_path = Path(state["cases"])
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    from .lockfiles import expand

    pins = sorted(
        [*cases["shared_pins"]]
        + [pin for name, value in state["components"].items() for pin in expand(name, str(value))]
    )
    cases["project"] = str((cases_path.parent / cases["project"]).resolve())
    root = (cases_path.parent / cases.get("environments", ".regressleuth-envs")).resolve()
    venv, compatible, _detail = environment_for(cases, pins, root, find_uv())
    if not compatible:
        args.result.write_text(json.dumps({"status": "incompatible"}), encoding="utf-8")
        return 0
    metric = outcome(cases, venv, args.result.with_suffix(".junit.xml"))
    if metric is None:
        return 3
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
