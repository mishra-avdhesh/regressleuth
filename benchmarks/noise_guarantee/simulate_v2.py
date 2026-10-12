"""Version 2 of the pre-registered noise-guarantee simulation (see PROTOCOL_V2.md).

python benchmarks/noise_guarantee/simulate_v2.py smoke    # counts only
python benchmarks/noise_guarantee/simulate_v2.py freeze
python benchmarks/noise_guarantee/simulate_v2.py run      # one run, refuses a rerun
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from simulate import ALPHA, BASE, PROJECT, THRESHOLD, clopper_pearson_upper

from regressleuth import Incident, investigate
from regressleuth.strategies import STRATEGIES

OUTPUT = PROJECT / "benchmarks" / "results" / "noise_guarantee_v2"
FREEZE = HERE / "FREEZE_V2.json"
SCENARIOS = ("masked_healing", "stress_near")
AUDITS: tuple[int | str, ...] = ("extended", 0)
SIZES = (4, 6, 8)
INTERVALS = ("anytime", "student_t", "normal")
SIGMA = 0.5 * THRESHOLD
INCIDENTS = 200
SMOKE_SEED_OFFSET = 10_000_000


def world(scenario: str, k: int, seed: int) -> dict[str, Any]:
    rng = random.Random(f"v2|{scenario}|{k}|{seed}")
    components = [f"c{i}" for i in range(k)]
    pool = components.copy()
    rng.shuffle(pool)
    if scenario == "masked_healing":
        size = rng.choice((1, 2))
        cause, pool = pool[:size], pool[size:]
        healer, guard = pool[0], pool[1]
        return {
            "components": components,
            "cause": cause,
            "healer": healer,
            "guard": guard,
            "drop": rng.uniform(1.5, 4.0) * THRESHOLD,
            "decoy": None,
            "decoy_effect": 0.0,
        }
    return {
        "components": components,
        "cause": [pool[0]],
        "healer": None,
        "guard": None,
        "drop": rng.uniform(1.0, 1.1) * THRESHOLD,
        "decoy": pool[1],
        "decoy_effect": rng.uniform(0.85, 0.99) * THRESHOLD,
    }


def true_mean(spec: dict[str, Any], mask: frozenset[str]) -> float:
    value = BASE
    if spec["decoy"] is not None and spec["decoy"] in mask:
        value -= spec["decoy_effect"]
    if set(spec["cause"]) <= mask:
        healed = spec["healer"] is not None and spec["healer"] in mask and spec["guard"] not in mask
        if not healed:
            value -= spec["drop"]
    return value


def minimal_failing(spec: dict[str, Any]) -> set[frozenset[str]]:
    import itertools

    components = spec["components"]
    fails = {
        frozenset(mask)
        for size in range(1, len(components) + 1)
        for mask in itertools.combinations(components, size)
        if BASE - true_mean(spec, frozenset(mask)) >= THRESHOLD
    }
    return {mask for mask in fails if not any(other < mask for other in fails)}


def incident_for(k: int, interval: str, audit: int | str) -> Incident:
    replay: dict[str, Any] = {"repeats": 2, "max_repeats": 40, "confidence": 1 - ALPHA, "interval": interval}
    if interval == "anytime":
        replay["noise_scale"] = SIGMA
    components = [f"c{i}" for i in range(k)]
    return Incident.from_spec(
        {
            "version": "1.0",
            "id": f"sim2-k{k}",
            "good": dict.fromkeys(components, "good"),
            "bad": dict.fromkeys(components, "bad"),
            "metric": {"name": "score", "direction": "higher_is_better", "regression_threshold": THRESHOLD},
            "replay": replay,
            "search": {"max_cause_size": 2},
            "budget": {"audit": audit},
            "adapter": {"type": "python", "callable": "simulated:runner"},
        },
        base_dir=HERE,
    )


def one_cell(job: tuple[str, int, int]) -> list[dict[str, Any]]:
    scenario, k, seed = job
    spec = world(scenario, k, seed)
    accepted = minimal_failing(spec)

    def runner(state: dict[str, Any], _cases: Any, _metric: str, seed: int = 0) -> float:
        mask = frozenset(c for c, value in state.items() if value == "bad")
        key = f"v2noise|{scenario}|{k}|{job[2]}|{sorted(mask)}|{seed}"
        return true_mean(spec, mask) + random.Random(key).gauss(0.0, SIGMA)

    rows = []
    for audit in AUDITS:
        for interval in INTERVALS:
            incident = incident_for(k, interval, audit)
            for strategy in STRATEGIES:
                report = investigate(incident, budget=2**k, strategy=strategy, seed=0, executor=runner)
                diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
                correct = diagnosis in accepted if diagnosis is not None else False
                rows.append(
                    {
                        "scenario": scenario,
                        "k": k,
                        "incident": seed,
                        "audit": audit,
                        "interval": interval,
                        "strategy": strategy,
                        "status": report.status,
                        "diagnosis": sorted(diagnosis) if diagnosis is not None else None,
                        "accepted": sorted(sorted(a) for a in accepted),
                        "wrong_verified": int(report.status == "verified" and not correct),
                        "correct_verified": int(report.status == "verified" and correct),
                        "runs": report.total_runs,
                    }
                )
    return rows


def jobs(offset: int, count: int) -> list[tuple[str, int, int]]:
    return [(scenario, k, offset + i) for scenario in SCENARIOS for k in SIZES for i in range(count)]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], str(row["audit"]), row["interval"], row["strategy"])].append(row)
    table = []
    for (scenario, audit, interval, strategy), values in sorted(groups.items()):
        n = len(values)
        wrong = sum(v["wrong_verified"] for v in values)
        table.append(
            {
                "scenario": scenario,
                "audit": audit,
                "interval": interval,
                "strategy": strategy,
                "investigations": n,
                "wrong_verified": wrong,
                "wrong_verified_rate": wrong / n,
                "wrong_verified_upper95": clopper_pearson_upper(wrong, n),
                "correct_verified_rate": sum(v["correct_verified"] for v in values) / n,
                "mean_runs": sum(v["runs"] for v in values) / n,
            }
        )
    primary = [row for row in table if row["interval"] == "anytime"]
    supported = all(
        r["wrong_verified_rate"] <= ALPHA and r["wrong_verified_upper95"] <= ALPHA for r in primary
    )
    return {"alpha": ALPHA, "primary_supported": supported, "table": table}


def report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Noise-guarantee simulation, version 2 (pre-registered, one run)",
        "",
        "Protocol: [PROTOCOL_V2.md](../../noise_guarantee/PROTOCOL_V2.md). Version 1 is unchanged: "
        "[report](../noise_guarantee/REPORT.md).",
        "",
        f"**Primary claim supported: {'yes' if summary['primary_supported'] else 'NO'}.**",
        "",
        "| scenario | audit | interval | strategy | investigations | wrong verified | rate | 95% upper | correct verified | mean runs |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["table"]:
        lines.append(
            f"| {row['scenario']} | {row['audit']} | {row['interval']} | {row['strategy']} | "
            f"{row['investigations']} | **{row['wrong_verified']}** | {row['wrong_verified_rate']:.4f} | "
            f"{row['wrong_verified_upper95']:.4f} | {row['correct_verified_rate']:.3f} | {row['mean_runs']:.1f} |"
        )
    lines += ["", "Rows of one incident share noise draws (paired). All rows: `rows.json`.", ""]
    return "\n".join(lines)


def frozen_files() -> dict[str, str]:
    files = [HERE / "PROTOCOL_V2.md", HERE / "simulate_v2.py", HERE / "simulate.py"]
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
            rows = [row for cell in pool.map(one_cell, jobs(SMOKE_SEED_OFFSET, 1)) for row in cell]
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
        rows = [row for cell in pool.map(one_cell, jobs(0, INCIDENTS), chunksize=4) for row in cell]
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
    print(f"{len(rows)} investigations; primary claim supported: {summary['primary_supported']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
