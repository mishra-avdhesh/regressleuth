"""Replay one dependency mix of a drift incident (the command adapter's runner).

    python runner.py --state STATE.json --result RESULT.json

The state names a version, or ``absent``, for every changed distribution. The runner
installs exactly the pinned union (``--no-deps``, wheels only) with the project's own
wheel into a cached virtual environment keyed by the pin set. It then runs the incident's
fixed pytest node IDs on the fixed commit. It writes ``{"metric": 1.0}`` if every node
passed, ``{"metric": 0.0}`` if any failed, errored or was skipped, and
``{"status": "incompatible"}`` if the mix cannot be installed or ``uv pip check`` reports
a requirement conflict. Anything else (unknown node IDs, a pytest crash, no uv) exits
non-zero and is a replay error.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DRIFT = Path(__file__).resolve().parent
WORK = DRIFT / "work"
UV = Path(__file__).resolve().parents[2] / ".venv" / "bin" / "uv"


def uv(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(UV), *args], capture_output=True, text=True, env=env, check=False)


def altered_files(venv: Path) -> list[str]:
    """Installed files whose content matches no sha256 any wheel RECORD lists for that path.

    Several wheels may install the same path (some ship a top-level ``docs/``); the file then
    holds one of their versions, which is a collision, not tampering.
    """
    import base64
    import csv

    altered = []
    for site in venv.glob("lib/python3.*/site-packages"):
        expected: dict[str, set[str]] = {}
        for record in site.glob("*.dist-info/RECORD"):
            for row in csv.reader(record.read_text().splitlines()):
                if len(row) >= 2 and row[1].startswith("sha256=") and not row[0].endswith(".pyc"):
                    expected.setdefault(row[0], set()).add(row[1][7:])
        for name, digests in expected.items():
            path = site / name
            if path.is_file():
                digest = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b"=")
                if digest.decode() not in digests:
                    altered.append(name)
    return altered


def environment_for(pins: list[str], python: str, wheel: Path, env: dict[str, str]) -> tuple[Path, bool]:
    """Return (venv, compatible). Built once per pin set; concurrent callers wait on a lock."""
    key = hashlib.sha256("\n".join([python, wheel.name, *pins]).encode()).hexdigest()[:24]
    venv = WORK / "envs" / key
    venv.parent.mkdir(parents=True, exist_ok=True)
    with open(venv.parent / f"{key}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = venv / "regressleuth-env.json"
        if marker.exists():
            return venv, json.loads(marker.read_text())["compatible"]
        if venv.exists():  # left unfinished by an interrupted build: start again
            shutil.rmtree(venv)
        created = uv("venv", "--quiet", "--python", python, str(venv), env=env)
        if created.returncode != 0:
            raise SystemExit(f"could not create a Python {python} environment: {created.stderr[-500:]}")
        requirements = venv / "pins.txt"
        requirements.write_text("\n".join(pins) + "\n")
        python_path = str(venv / "bin" / "python")
        installed = uv(
            "pip",
            "install",
            "--quiet",
            "--python",
            python_path,
            "--no-deps",
            "--only-binary",
            ":all:",
            "-r",
            str(requirements),
            str(wheel),
            env=env,
        )
        compatible = installed.returncode == 0
        detail = installed.stderr[-2000:]
        if compatible:
            tampered = altered_files(venv)
            if tampered:
                raise SystemExit(f"installed files differ from their wheel RECORD hashes: {tampered[:5]}")
            checked = uv("pip", "check", "--python", python_path, env=env)
            compatible = checked.returncode == 0
            detail = (checked.stdout + checked.stderr)[-2000:]
        marker.write_text(json.dumps({"compatible": compatible, "detail": detail, "pins": pins}, indent=1))
        return venv, compatible


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    pins = sorted(
        [*cases["shared_pins"]]
        + [f"{name}=={version}" for name, version in state["components"].items() if version != "absent"]
    )
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(WORK)),
        "UV_CACHE_DIR": str(WORK / "uv-cache"),
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_NO_PROGRESS": "1",
    }
    source = WORK / "sources" / cases["incident"]
    wheel = WORK / "wheels" / cases["incident"] / cases["project_wheel"]
    if not wheel.exists() or not source.exists():
        raise SystemExit("project source or wheel missing; run drift.py fetch first")
    venv, compatible = environment_for(pins, cases["python"], wheel, env)
    if not compatible:
        args.result.write_text(json.dumps({"status": "incompatible"}), encoding="utf-8")
        return 0
    report = args.result.with_suffix(".junit.xml")
    zoneinfo = WORK / "tzdb" / "tzdata" / "zoneinfo"
    if not zoneinfo.is_dir():
        raise SystemExit("host time-zone database missing; run drift.py replay, which prepares it")
    test_env = {
        **env,
        # a complete IANA database as a normal Linux host provides (this machine lacks legacy names)
        "PYTHONTZPATH": str(zoneinfo),
        "PYTHONHASHSEED": "0",
        "MPLBACKEND": "Agg",
        "PYTHONDONTWRITEBYTECODE": "1",
        **cases.get("test_environment", {}),
    }
    completed = subprocess.run(
        [
            str(venv / "bin" / "python"),
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:randomly",
            f"--junitxml={report}",
            "-o",
            "addopts=",
            *cases.get("pytest_args", []),
            *cases["tests"],
        ],
        cwd=source / cases.get("test_root", "."),
        env=test_env,
        capture_output=True,
        text=True,
        timeout=cases.get("test_timeout_seconds", 600),
        check=False,
    )
    cases_run = list(ET.parse(report).getroot().iter("testcase")) if report.exists() else []
    # a test module that cannot even be imported under this mix did not pass
    collection_failed = any(
        child.tag == "error" and child.get("message") == "collection failure"
        for c in cases_run
        for child in c
    )
    if collection_failed:
        args.result.write_text(json.dumps({"metric": 0.0}), encoding="utf-8")
        return 0
    if completed.returncode not in (0, 1, 2) or not report.exists():
        sys.stderr.write(completed.stdout[-3000:] + completed.stderr[-3000:])
        return 3
    failed = [c for c in cases_run if any(child.tag in {"failure", "error", "skipped"} for child in c)]
    if completed.returncode == 0 and len(cases_run) < len(cases["tests"]):
        sys.stderr.write(f"expected {len(cases['tests'])} tests, ran {len(cases_run)}\n")
        return 3
    passed = completed.returncode == 0 and not failed
    args.result.write_text(json.dumps({"metric": 1.0 if passed else 0.0}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
