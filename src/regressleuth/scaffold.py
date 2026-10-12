"""Files written by `regressleuth init`: a runnable starting point for your own pipeline."""

from __future__ import annotations

INCIDENT = """# Regressleuth Incident Specification 1.0 (docs/INCIDENT_SPEC.md)
version: "1.0"
id: my_incident
description: Accuracy dropped after the October release.

good:                      # the known-good deployment
  model: models/v4
  preprocessing: prep_commit_a1b2c3
  config: config_a.yaml
  data: snapshots/2026-09-01
bad:                       # the regressed deployment
  model: models/v5
  preprocessing: prep_commit_d4e5f6
  config: config_b.yaml
  data: snapshots/2026-10-01

metric:
  name: accuracy
  direction: higher_is_better
  regression_threshold: 0.05     # a drop this large counts as the regression

replay:                    # deterministic runs: keep repeats at 1
  repeats: 1
  max_repeats: 1
  confidence: 0.95
  interval: student_t
  # Noisy metric (different seeds give different scores)? Without a noise bound the
  # result stops at "inferred". For "verified" with P(wrong) <= 1 - confidence, use:
  #   repeats: 3
  #   max_repeats: 24
  #   interval: anytime
  #   noise_scale: 0.004     # upper bound on one run's SD, e.g. from seeds of the good state

search:
  strategy: adaptive
  max_cause_size: 2

budget:
  max_replays: 16          # isolation replays, including both endpoints
  audit: extended

cases: cases.json          # the SAME labeled cases are scored in every replay

adapter:
  type: command
  command: ["{python}", "runner.py", "--state", "{state}", "--result", "{result}"]
  timeout_seconds: 300
"""

RUNNER = '''"""Replay runner: regressleuth calls this once per combination of good/bad versions.

It receives --state (JSON: {"components": {...}, "cases": "<path>", "metric": "...",
"seed": 0}) and must write --result as {"metric": <number>} or {"status": "incompatible"}.
Edit `load_system` and `predict` to build your real pipeline from the component values.
The same cases file and labels must be used for every replay.
"""

import argparse
import json
from pathlib import Path


def load_system(components: dict):
    """TODO: build the pipeline from `components`, e.g. load the model at
    components["model"], apply the preprocessing version, read the config and data."""
    return components


def predict(system: dict, case: dict) -> int:
    """TODO: run one case through the pipeline and return the predicted label.
    This placeholder fails only when the NEW model meets the NEW preprocessing, so
    `regressleuth diagnose incident.yaml` has an interaction to find out of the box."""
    broken = system["model"].endswith("v5") and system["preprocessing"].endswith("d4e5f6")
    return 1 - case["label"] if broken and case["case_id"] % 2 == 0 else case["label"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    system = load_system(state["components"])
    correct = sum(predict(system, case) == case["label"] for case in cases)
    args.result.write_text(json.dumps({"metric": correct / len(cases)}), encoding="utf-8")


if __name__ == "__main__":
    main()
'''

CASES = "[" + ",".join(f'{{"case_id": {i}, "label": {i % 2}}}' for i in range(20)) + "]\n"

README = """# My regression investigation

1. Put your real good and bad versions in `incident.yaml` (any JSON values the runner understands).
2. Implement `load_system` and `predict` in `runner.py`; keep `cases.json` fixed for every replay.
3. `regressleuth inspect incident.yaml` shows the search before anything runs.
4. `regressleuth diagnose incident.yaml` runs it.

Use `--format html --output report.html` for a shareable report.
"""

FILES = {
    "incident.yaml": INCIDENT,
    "runner.py": RUNNER,
    "cases.json": CASES,
    "README.md": README,
}
