"""Run the bundled dependency-upgrade example with real uv as a release smoke test."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCIDENT = ROOT / "examples" / "lockfile_upgrade" / "incident" / "incident.yaml"


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "regressleuth.cli", "diagnose", str(INCIDENT), "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if completed.returncode:
        print(completed.stderr or completed.stdout, file=sys.stderr)
        return completed.returncode
    result = json.loads(completed.stdout)
    actual = (
        result.get("status"),
        result.get("diagnosis"),
        result.get("verification", {}).get("audit_mode"),
        len(result.get("experiments", [])),
    )
    expected = ("verified", ["pandas"], "extended", 8)
    if actual != expected:
        print(f"real uv lockfile example: expected {expected!r}, got {actual!r}", file=sys.stderr)
        return 1
    print("real uv lockfile example: pandas verified under extended audit in 8 replays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
