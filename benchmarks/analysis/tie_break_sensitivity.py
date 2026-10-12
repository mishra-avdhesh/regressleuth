"""Measure budget-8 sensitivity to arbitrary component-name ordering.

This replays the sealed holdout observation tables in memory. Only the five
changed component names are permuted; component values, outcomes, noise
realizations, truth, and the search implementation are unchanged.

Run from anywhere with::

    python3 benchmarks/analysis/tie_break_sensitivity.py
"""

from __future__ import annotations

import itertools
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))

from evaluate import load, lookup
from seal import digest as seal_digest

from regressleuth import investigate

SUITE = ROOT / "benchmarks" / "holdout"
STRATEGIES = ("adaptive", "ddmin")
BUDGET = 8
NEUTRAL_NAMES = tuple(f"component_{i}" for i in range(5))


def renamed_table(table: dict, mapping: dict[str, str]) -> dict:
    """Rename the changed components in each stored observation key."""
    return {
        "|".join(sorted(mapping[name] for name in key.split("|") if name)): observations
        for key, observations in table.items()
    }


def main() -> None:
    sealed = json.loads((SUITE / "SEAL.json").read_text(encoding="utf-8"))["files"]
    if seal_digest(SUITE) != sealed:
        raise RuntimeError("holdout seal is broken; restore the sealed inputs before running")
    truth = json.loads((SUITE / "ground_truth.json").read_text(encoding="utf-8"))
    counts = {strategy: 0 for strategy in STRATEGIES}
    total = 0
    print("incident,permutations,adaptive_verified_right,ddmin_verified_right")
    for path in sorted((SUITE / "incidents").glob("*.yaml")):
        incident = load(path)
        components = incident.changed_components
        if len(components) != len(NEUTRAL_NAMES):
            raise ValueError(f"{incident.id}: expected five changed components")
        table_path = SUITE / "results" / "tables" / f"{incident.id}.json"
        table = json.loads(table_path.read_text(encoding="utf-8"))["table"]
        incident_counts = {strategy: 0 for strategy in STRATEGIES}
        permutations = 0
        for neutral_names in itertools.permutations(NEUTRAL_NAMES):
            mapping = dict(zip(components, neutral_names, strict=True))
            renamed = replace(
                incident,
                good={mapping.get(name, name): value for name, value in incident.good.items()},
                bad={mapping.get(name, name): value for name, value in incident.bad.items()},
            )
            observations = renamed_table(table, mapping)
            expected = frozenset(mapping[name] for name in truth[incident.id])
            evaluator = lookup(renamed, observations)
            for strategy in STRATEGIES:
                report = investigate(
                    renamed,
                    budget=BUDGET,
                    strategy=strategy,
                    seed=0,
                    executor=evaluator,
                    audit="full",
                    max_cause_size=2,
                )
                if report.status == "verified" and frozenset(report.diagnosis) == expected:
                    incident_counts[strategy] += 1
            permutations += 1
        total += permutations
        for strategy in STRATEGIES:
            counts[strategy] += incident_counts[strategy]
        print(f"{incident.id},{permutations},{incident_counts['adaptive']},{incident_counts['ddmin']}")
    print(f"ALL,{total},{counts['adaptive']},{counts['ddmin']}")


if __name__ == "__main__":
    main()
