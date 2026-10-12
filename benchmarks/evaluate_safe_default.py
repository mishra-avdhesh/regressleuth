"""Secondary release-safety evaluation: product defaults, stored replay tables."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import evaluate

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "safe_default"


def main() -> int:
    suites = evaluate.suites()
    for name in ("development", "holdout"):
        suite = suites[name]
        if suite["sealed"]:
            check = subprocess.run(
                [sys.executable, str(ROOT / "seal.py"), "verify", str(suite["dir"])],
                check=False,
            )
            if check.returncode:
                return check.returncode
        for path in [
            *suite["incidents"],
            *(p for p in suite["controls"] if p.name != "expected_status.json"),
        ]:
            incident = evaluate.load(path)
            if not (suite["tables"] / f"{incident.id}.json").is_file():
                raise FileNotFoundError(f"stored replay table missing for {incident.id}")
    rows = []
    for name in ("development", "holdout"):
        print(f"evaluating safe default: {name}", flush=True)
        rows.extend(evaluate.evaluate_suite(name, suites[name], interval="student_t", audits=("extended",)))
    summary = evaluate.summarize(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.json").write_text(json.dumps(rows, indent=1) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    lines = [
        "# Secondary release-safety evaluation: current product defaults",
        "",
        "The product profile uses `audit: extended` and `replay.interval: student_t`. It is",
        "evaluated on the same stored observations as the frozen published evaluation. This",
        "post-hoc result is descriptive and was not used to tune the search algorithm.",
        "The original published results remain in `../evaluation/`.",
        "",
        "| suite | strategy | isolation budget | verified right | false verified controls | mean isolation | mean total |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['suite']} | {row['strategy']} | {row['budget']} | "
            f"{row['verified_right']:.1%} | {row['controls_false_verified']:.1%} | "
            f"{row['mean_isolation_replays']:.1f} | {row['mean_total_replays']:.1f} |"
        )
    (OUT / "EVALUATION.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT / 'EVALUATION.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
