"""Freeze the search method and fingerprint its behavior.

`python benchmarks/freeze_method.py write` records, at a single moment:
  * SHA-256 of every algorithm and benchmark source file and of the incident manifests,
  * the method's hyperparameters, thresholds, replay semantics and assumptions,
  * a behavioral trace: a digest of the exact ordered replay sequence and diagnosis of every
    strategy on every synthetic incident at several budgets.
`python benchmarks/freeze_method.py verify` recomputes the traces and fails on any difference,
which proves the default method still behaves exactly as frozen even when files were refactored.
New capabilities must be opt-in and leave the default path byte-for-byte identical.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "src"))

from regressleuth.bench import build_suite, run_one
from regressleuth.strategies import STRATEGIES

FROZEN = ROOT / "frozen"
MANIFEST = FROZEN / "frozen_method.json"
SOURCES = [
    "src/regressleuth/engine.py",
    "src/regressleuth/strategies.py",
    "src/regressleuth/models.py",
    "src/regressleuth/executor.py",
    "src/regressleuth/bench.py",
    "src/regressleuth/api.py",
    "benchmarks/run_real.py",
    "benchmarks/validate_fixtures.py",
    "benchmarks/build_incidents.py",
]
TRACE_BUDGETS = (4, 6, 8, 12, 16, 32)
TRACE_RANDOM_SEEDS = 3

METHOD = {
    "name": "regressleuth adaptive search (0.1.0a1 default configuration)",
    "hypothesis_space": {
        "max_cause_size": 2,
        "description": "all singletons and all pairs of changed components",
    },
    "cause_model": "one deterministic, inclusion-minimal conjunction: F(S) is true exactly when h is a subset of S",
    "adaptive_objective": "replay the unseen mask whose predicted failures split the remaining hypotheses closest to evenly "
    "(maximizes 2*p*(1-p) with p = fraction of hypotheses predicting FAIL); uniform prior, unit replay cost",
    "tie_break": "smaller mask first, then lexicographic order of sorted component names",
    "elimination": "a pass or fail outcome removes every hypothesis predicting the other outcome; "
    "inconclusive, incompatible and error outcomes prune nothing",
    "verification": "unique hypothesis whose own mask failed and whose proper subsets all passed",
    "audit": {
        "default": "full",
        "masks": "complement of the all-bad state minus each cause component (expected pass), "
        "and the cause plus each one other component (expected fail)",
        "budget": "separate from the isolation budget; failure to complete the audit yields status inferred; "
        "any contradiction yields assumption_violated",
    },
    "regression_rule": {
        "deterministic": "FAIL when sign*(mean(good)-mean(mask)) >= threshold - 1e-12 else PASS",
        "noisy": "FAIL if effect - z*se >= threshold; PASS if effect + z*se < threshold; else inconclusive "
        "(more runs up to max_repeats)",
        "default_confidence": 0.95,
        "default_repeats": 1,
        "tolerance": 1e-12,
    },
    "budget_semantics": "budget counts both endpoint replays, search replays and minimality-verification replays; "
    "the audit is extra and reported separately; a replay is one mask evaluation regardless of repeats",
    "endpoint_rules": "F(empty) false and F(all-bad) true must hold, else the result is invalid_baseline or evaluation error",
    "assumptions": [
        "replays depend only on the declared components and the run seed",
        "the evaluation cohort and labels are identical in every replay",
        "failure is monotone in the set of bad components for the true cause",
        "the cause has at most two components",
    ],
}
BENCHMARK = {
    "budgets": [4, 6, 8, 12, 16, 32],
    "random_seeds": 10,
    "bootstrap": {"rounds": 1000, "seed": 20261008, "interval": 0.95},
    "synthetic_suite": "regressleuth.bench.build_suite() at freeze time",
    "real_incident_runner": "benchmarks/run_real.py with cached replay tables in benchmarks/results/tables",
    "fairness": "every strategy replays against identical metric tables and identical seeded noise",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace_digest(report: Any) -> str:
    payload = {
        "diagnosis": report.diagnosis,
        "experiments": [[list(e.changed), e.outcome, e.role] for e in report.experiments],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def behavioral_trace() -> dict[str, str]:
    traces: dict[str, str] = {}
    for spec in build_suite():
        for strategy in STRATEGIES:
            seeds = range(TRACE_RANDOM_SEEDS) if strategy == "random" else range(1)
            for budget in TRACE_BUDGETS:
                for seed in seeds:
                    key = f"{spec.id}|{strategy}|{budget}|{seed}"
                    traces[key] = trace_digest(run_one(spec, strategy, budget, seed))
    return traces


def build_manifest() -> dict[str, Any]:
    files = {rel: sha256_file(REPO / rel) for rel in SOURCES}
    tree = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(files.items())).encode()).hexdigest()
    incidents = {p.name: sha256_file(p) for p in sorted((ROOT / "incidents").glob("*.json"))}
    return {
        "manifest_version": 1,
        "frozen_on": "2026-10-08",
        "package_version": "0.1.0a1",
        "source": {
            "git_commit": None,
            "note": "the project was not a git repository at freeze time, so the tree hash below is the source hash",
            "tree_sha256": tree,
            "files": files,
        },
        "method": METHOD,
        "benchmark_configuration": BENCHMARK,
        "development_incidents": {
            "manifests_sha256": incidents,
            "ground_truth_sha256": sha256_file(ROOT / "ground_truth.json"),
        },
        "behavioral_trace": {
            "file": "benchmarks/frozen/synthetic_trace.json",
            "budgets": list(TRACE_BUDGETS),
            "random_seeds": TRACE_RANDOM_SEEDS,
            "fields": "per (incident, strategy, budget, seed): digest of diagnosis and ordered (mask, outcome, role)",
        },
        "rule": "No tuning of the method using any result from the holdout benchmark. A failing holdout "
        "incident is reported, not fixed.",
    }


def main(mode: str) -> int:
    FROZEN.mkdir(exist_ok=True)
    trace_path = FROZEN / "synthetic_trace.json"
    if mode == "write":
        traces = behavioral_trace()
        trace_path.write_text(json.dumps(traces, indent=0, sort_keys=True), encoding="utf-8")
        manifest = build_manifest()
        manifest["behavioral_trace"]["entries"] = len(traces)
        manifest["behavioral_trace"]["file_sha256"] = sha256_file(trace_path)
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"froze {len(traces)} behavioral traces; tree sha256 {manifest['source']['tree_sha256'][:16]}")
        return 0
    expected = json.loads(trace_path.read_text(encoding="utf-8"))
    actual = behavioral_trace()
    changed = sorted(k for k in expected if expected[k] != actual.get(k))
    extra = sorted(set(actual) - set(expected))
    if changed:
        print(f"BEHAVIOR CHANGED in {len(changed)} frozen traces; first: {changed[:3]}")
        return 1
    print(
        f"frozen behavior intact: {len(expected)} traces identical"
        + (f" ({len(extra)} traces from incidents added after the freeze, not compared)" if extra else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "verify"))
