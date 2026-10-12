"""Prove each incident's ground truth by replaying every combination of components.

Usage: python benchmarks/prove_ground_truth.py SUITE_DIR [incident-prefix ...]

SUITE_DIR contains incidents/*.yaml (Incident Specification 1.0) and ground_truth.json.
For every incident, all 2^k combinations are replayed (runs = replay.max_repeats, each
with its own seed) and the mean metric compared with the known-good mean. The proof holds
when a combination regresses by at least the threshold *if and only if* it contains the
declared cause. The raw observation table is stored in SUITE_DIR/results/tables/ so that
every strategy is later evaluated on identical observations, noise and incompatibilities.
"""

from __future__ import annotations

import itertools
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regressleuth import Incident
from regressleuth.adapters import build_adapter
from regressleuth.adapters.base import ReplayRequest


def table_for(incident: Incident, workers: int) -> dict[str, list[dict[str, Any]]]:
    components = incident.changed_components
    runs = incident.replay.max_repeats
    jobs = [
        (frozenset(combo), seed)
        for size in range(len(components) + 1)
        for combo in itertools.combinations(components, size)
        for seed in range(runs)
    ]

    def one(job: tuple[frozenset[str], int]) -> dict[str, Any]:
        mask, seed = job
        adapter = build_adapter(incident)
        outcome = adapter.replay(
            ReplayRequest(incident.selected_state(mask), seed, incident.replay.metric, incident.replay.cases)
        )
        adapter.close()
        return {
            "status": outcome.status,
            "metric": outcome.metric,
            "error_kind": outcome.error_kind,
            "seconds": outcome.duration_seconds,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, jobs))
    table: dict[str, list[dict[str, Any]]] = {}
    for (mask, _seed), result in zip(jobs, results, strict=True):
        table.setdefault("|".join(sorted(mask)), []).append(result)
    return table


def prove(
    incident: Incident, cause: frozenset[str], table: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    sign = 1.0 if incident.replay.direction == "higher" else -1.0
    threshold = incident.replay.regression_threshold
    errors = {k: [r for r in v if r["status"] != "ok"] for k, v in table.items()}
    if any(errors.values()):
        bad = {k: v[0]["status"] + ":" + str(v[0]["error_kind"]) for k, v in errors.items() if v}
        return {"proved": False, "reason": f"replays did not produce metrics: {bad}"}
    means = {k: statistics.fmean(r["metric"] for r in v) for k, v in table.items()}
    base = means[""]
    violations, margin, closest = [], float("inf"), ""
    for key, mean in means.items():
        mask = frozenset(key.split("|")) if key else frozenset()
        drop = sign * (base - mean)
        regressed = drop >= threshold - 1e-12
        if abs(drop - threshold) < margin:
            margin, closest = abs(drop - threshold), key or "(none)"
        if regressed != cause.issubset(mask):
            violations.append(
                {
                    "mask": key or "(none)",
                    "drop": round(drop, 4),
                    "expected": "regress" if cause.issubset(mask) else "no regression",
                }
            )
    sds = [statistics.stdev(r["metric"] for r in v) for v in table.values() if len(v) > 1]
    return {
        "proved": not violations,
        "baseline": round(base, 4),
        "endpoint_drop": round(sign * (base - means["|".join(sorted(incident.changed_components))]), 4),
        "combinations": len(table),
        "runs_per_combination": len(next(iter(table.values()))),
        "closest_margin_to_threshold": round(margin, 4),
        "closest_combination": closest,
        "max_run_sd": round(max(sds), 4) if sds else 0.0,
        "violations": violations,
    }


def main(suite: Path, prefixes: tuple[str, ...]) -> int:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    truth = json.loads((suite / "ground_truth.json").read_text(encoding="utf-8"))
    tables = suite / "results" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    proofs: dict[str, Any] = {}
    failed = 0
    for path in sorted((suite / "incidents").glob("*.yaml")):
        if prefixes and not path.stem.startswith(prefixes):
            continue
        incident = Incident.from_file(path)
        started = time.perf_counter()
        table = table_for(incident, workers=12)
        (tables / f"{incident.id}.json").write_text(
            json.dumps({"incident": incident.id, "table": table}), encoding="utf-8"
        )
        proof = prove(incident, frozenset(truth[incident.id]), table)
        proof["seconds"] = round(time.perf_counter() - started, 1)
        proofs[incident.id] = proof
        failed += not proof["proved"]
        status = "PROVED" if proof["proved"] else "FAILED"
        print(f"{status} {incident.id}: {json.dumps({k: v for k, v in proof.items() if k != 'violations'})}")
        for violation in proof.get("violations", [])[:6]:
            print(f"   violation {violation}")
    existing = suite / "results" / "ground_truth_proofs.json"
    merged = json.loads(existing.read_text()) if existing.exists() and prefixes else {}
    merged.update(proofs)
    existing.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]).resolve(), tuple(sys.argv[2:])))
