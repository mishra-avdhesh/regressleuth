"""Re-run the explicitly frozen full-audit/normal-interval profile into a new directory."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import evaluate

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "frozen_2026_10_08.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output == evaluate.OUT.resolve():
        parser.error("output must differ from the published results directory")
    config = json.loads(CONFIG.read_text())
    if config["audit"] != "full" or config["interval"] != "normal":
        raise ValueError("frozen configuration changed")
    check = subprocess.run([sys.executable, str(ROOT / "freeze_method.py"), "verify"], check=False)
    if check.returncode:
        return check.returncode
    suites = evaluate.suites()
    for name in config["suites"]:
        suite = suites[name]
        for path in [
            *suite["incidents"],
            *(p for p in suite["controls"] if p.name != "expected_status.json"),
        ]:
            incident = evaluate.load(path)
            if not (suite["tables"] / f"{incident.id}.json").is_file():
                raise FileNotFoundError(f"stored replay table missing for {incident.id}")
    evaluate.OUT = output
    return evaluate.main(tuple(config["suites"]), interval="normal", audits=("full",))


if __name__ == "__main__":
    raise SystemExit(main())
