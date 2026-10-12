"""Pre-registered large-search-space study (see PROTOCOL.md).

python benchmarks/scale/scale.py smoke    # 1 incident per cell, prints counts only
python benchmarks/scale/scale.py freeze
python benchmarks/scale/scale.py run      # one run, refuses a rerun
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
import sys
import time
import tracemalloc
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from regressleuth import Incident, investigate
from regressleuth.strategies import STRATEGIES

OUTPUT = PROJECT / "benchmarks" / "results" / "scale"
FREEZE = HERE / "FREEZE.json"
SCENARIOS = ("single", "pair", "masked_healing")
SIZES = (8, 10, 12)
BUDGETS: tuple[int | str, ...] = (8, 12, 16, 24, 32, "full")
RANDOM_SEEDS = 5
INCIDENTS = 100
SMOKE_SEED_OFFSET = 10_000_000


def world(scenario: str, k: int, seed: int) -> dict[str, Any]:
    rng = random.Random(f"scale|{scenario}|{k}|{seed}")
    pool = [f"c{i:02d}" for i in range(k)]
    rng.shuffle(pool)
    if scenario == "single":
        return {"cause": pool[:1], "healer": None, "guard": None}
    if scenario == "pair":
        return {"cause": pool[:2], "healer": None, "guard": None}
    size = rng.choice((1, 2))
    return {"cause": pool[:size], "healer": pool[size], "guard": pool[size + 1]}


def fails(spec: dict[str, Any], mask: frozenset[str]) -> bool:
    if not set(spec["cause"]) <= mask:
        return False
    return not (spec["healer"] is not None and spec["healer"] in mask and spec["guard"] not in mask)


def minimal_failing(spec: dict[str, Any], k: int) -> set[frozenset[str]]:
    # every failing mask contains the cause, and the cause itself fails, so it is the only one
    cause = frozenset(spec["cause"])
    assert fails(spec, cause)
    for size in range(1, len(cause)):
        assert not any(fails(spec, frozenset(sub)) for sub in itertools.combinations(cause, size))
    return {cause}


def incident_for(k: int) -> Incident:
    components = [f"c{i:02d}" for i in range(k)]
    return Incident.from_spec(
        {
            "version": "1.0",
            "id": f"scale-k{k}",
            "good": dict.fromkeys(components, "good"),
            "bad": dict.fromkeys(components, "bad"),
            "metric": {"name": "score", "direction": "higher_is_better", "regression_threshold": 0.5},
            "adapter": {"type": "python", "callable": "oracle:runner"},
        },
        base_dir=HERE,
    )


def one_incident(job: tuple[str, int, int]) -> list[dict[str, Any]]:
    scenario, k, seed = job
    spec = world(scenario, k, seed)
    accepted = minimal_failing(spec, k)
    incident = incident_for(k)

    def runner(state: dict[str, Any], *_args: Any) -> float:
        mask = frozenset(c for c, value in state.items() if value == "bad")
        return 0.0 if fails(spec, mask) else 1.0

    rows = []
    for strategy in STRATEGIES:
        for budget in BUDGETS:
            limit = 2**k if budget == "full" else int(budget)
            for search_seed in range(RANDOM_SEEDS) if strategy == "random" else range(1):
                tracemalloc.start()
                started = time.perf_counter()
                report = investigate(
                    incident, budget=limit, strategy=strategy, seed=search_seed, executor=runner
                )
                elapsed = time.perf_counter() - started
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
                correct = diagnosis in accepted if diagnosis is not None else False
                rows.append(
                    {
                        "scenario": scenario,
                        "k": k,
                        "incident": seed,
                        "strategy": strategy,
                        "budget": budget,
                        "search_seed": search_seed,
                        "status": report.status,
                        "wrong_verified": int(report.status == "verified" and not correct),
                        "correct_verified": int(report.status == "verified" and correct),
                        "isolation_replays": report.isolation_replays,
                        "audit_replays": report.experiments_used - report.isolation_replays,
                        "total_replays": report.experiments_used,
                        "engine_seconds": elapsed,
                        "peak_bytes": peak,
                    }
                )
    return rows


def jobs(offset: int, count: int) -> list[tuple[str, int, int]]:
    return [(scenario, k, offset + i) for scenario in SCENARIOS for k in SIZES for i in range(count)]


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(wins, losses) + 1)) / 2**n
    return min(1.0, 2 * tail)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["k"], row["strategy"], str(row["budget"]))].append(row)
    table = []
    for (scenario, k, strategy, budget), values in sorted(groups.items()):
        n = len(values)
        table.append(
            {
                "scenario": scenario,
                "k": k,
                "strategy": strategy,
                "budget": budget,
                "runs": n,
                "wrong_verified": sum(v["wrong_verified"] for v in values),
                "correct_verified_rate": sum(v["correct_verified"] for v in values) / n,
                "status_rates": {
                    s: sum(v["status"] == s for v in values) / n
                    for s in sorted({v["status"] for v in values})
                },
                "mean_isolation": statistics.fmean(v["isolation_replays"] for v in values),
                "mean_audit": statistics.fmean(v["audit_replays"] for v in values),
                "mean_total": statistics.fmean(v["total_replays"] for v in values),
                "mean_engine_seconds": statistics.fmean(v["engine_seconds"] for v in values),
                "max_peak_mb": max(v["peak_bytes"] for v in values) / 2**20,
            }
        )
    feasibility = {
        strategy: {
            "mean_engine_seconds": statistics.fmean(
                r["engine_seconds"] for r in rows if r["k"] == 12 and r["strategy"] == strategy
            ),
            "max_peak_mb": max(r["peak_bytes"] for r in rows if r["k"] == 12 and r["strategy"] == strategy)
            / 2**20,
        }
        for strategy in STRATEGIES
    }
    feasible = all(v["mean_engine_seconds"] < 2 and v["max_peak_mb"] < 256 for v in feasibility.values())
    paired = []
    full = {
        (r["scenario"], r["k"], r["incident"], r["strategy"]): r
        for r in rows
        if r["budget"] == "full" and r["search_seed"] == 0
    }
    for scenario in ("single", "pair"):
        for k in SIZES:
            wins = losses = ties = 0
            for seed in sorted({key[2] for key in full if key[0] == scenario and key[1] == k}):
                a, d = full[(scenario, k, seed, "adaptive")], full[(scenario, k, seed, "ddmin")]
                cost_a = a["isolation_replays"] if a["correct_verified"] else math.inf
                cost_d = d["isolation_replays"] if d["correct_verified"] else math.inf
                if cost_a < cost_d:
                    wins += 1
                elif cost_d < cost_a:
                    losses += 1
                else:
                    ties += 1
            paired.append(
                {
                    "scenario": scenario,
                    "k": k,
                    "adaptive_wins": wins,
                    "ddmin_wins": losses,
                    "ties": ties,
                    "sign_test_p": sign_test(wins, losses),
                }
            )
    wrong_control = sum(r["wrong_verified"] for r in rows if r["scenario"] == "masked_healing")
    wrong_model = sum(r["wrong_verified"] for r in rows if r["scenario"] != "masked_healing")
    return {
        "feasibility_k12": feasibility,
        "feasibility_check_passed": feasible,
        "wrong_verified_model_scenarios": wrong_model,
        "wrong_verified_masked_healing": wrong_control,
        "adaptive_vs_ddmin_full_budget": paired,
        "table": table,
    }


def report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Large-search-space study (pre-registered, one run)",
        "",
        "Protocol: [PROTOCOL.md](../../scale/PROTOCOL.md). Synthetic oracle incidents: evidence about",
        "scaling and cost, not external validity.",
        "",
        f"- Wrong `verified`, single and pair scenarios: **{summary['wrong_verified_model_scenarios']}**",
        f"- Wrong `verified`, non-monotone masked-healing control: **{summary['wrong_verified_masked_healing']}**",
        f"- Feasibility at k = 12 (mean engine time < 2 s, peak traced memory < 256 MB): "
        f"**{'passed' if summary['feasibility_check_passed'] else 'FAILED'}**",
        "",
        "| strategy | mean engine s at k=12 | max peak MB at k=12 |",
        "|---|---:|---:|",
    ]
    for strategy, values in summary["feasibility_k12"].items():
        lines.append(f"| {strategy} | {values['mean_engine_seconds']:.3f} | {values['max_peak_mb']:.1f} |")
    lines += [
        "",
        "## Adaptive vs ddmin, isolation replays before a correct verified (full budget)",
        "",
        "| scenario | k | adaptive fewer | ddmin fewer | ties | sign test p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["adaptive_vs_ddmin_full_budget"]:
        lines.append(
            f"| {row['scenario']} | {row['k']} | {row['adaptive_wins']} | {row['ddmin_wins']} | {row['ties']} | "
            f"{row['sign_test_p']:.3g} |"
        )
    lines += [
        "",
        "## All cells",
        "",
        "| scenario | k | strategy | budget | wrong verified | correct verified | mean isolation | mean audit | mean total | engine s | statuses |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary["table"]:
        statuses = ", ".join(f"{s} {v:.2f}" for s, v in row["status_rates"].items())
        lines.append(
            f"| {row['scenario']} | {row['k']} | {row['strategy']} | {row['budget']} | **{row['wrong_verified']}** | "
            f"{row['correct_verified_rate']:.2f} | {row['mean_isolation']:.1f} | {row['mean_audit']:.1f} | "
            f"{row['mean_total']:.1f} | {row['mean_engine_seconds']:.3f} | {statuses} |"
        )
    lines.append("")
    return "\n".join(lines)


def frozen_files() -> dict[str, str]:
    files = [HERE / "PROTOCOL.md", HERE / "scale.py"]
    files += sorted(
        p
        for p in (PROJECT / "src" / "regressleuth").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    return {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "smoke":
        with ProcessPoolExecutor() as pool:
            rows = [row for cell in pool.map(one_incident, jobs(SMOKE_SEED_OFFSET, 1)) for row in cell]
        report_markdown(summarize(rows))  # exercised, not shown
        print(f"smoke: {len(rows)} investigations completed")
        return 0
    if mode == "freeze":
        if FREEZE.exists():
            print("already frozen", file=sys.stderr)
            return 3
        files = frozen_files()
        FREEZE.write_text(
            json.dumps(
                {"frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": files},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print(f"froze {len(files)} files")
        return 0
    if mode != "run":
        print(__doc__, file=sys.stderr)
        return 2
    if (OUTPUT / "rows.json").exists():
        print("refusing to overwrite the existing run", file=sys.stderr)
        return 3
    if json.loads(FREEZE.read_text())["files"] != frozen_files():
        print("freeze broken", file=sys.stderr)
        return 1
    started = datetime.now(timezone.utc)
    with ProcessPoolExecutor() as pool:
        rows = [row for cell in pool.map(one_incident, jobs(0, INCIDENTS), chunksize=2) for row in cell]
    summary = summarize(rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "rows.json").write_text(json.dumps(rows, sort_keys=True) + "\n")
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    (OUTPUT / "RUN.json").write_text(
        json.dumps(
            {
                "started_utc": started.isoformat(timespec="seconds"),
                "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "freeze_sha256": hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
                "investigations": len(rows),
            },
            indent=2,
        )
        + "\n"
    )
    (OUTPUT / "REPORT.md").write_text(report_markdown(summary))
    print(f"{len(rows)} investigations; feasibility passed: {summary['feasibility_check_passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
