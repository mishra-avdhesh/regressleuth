"""Pre-registered simulation of the diagnosis-level error bound of ``interval: anytime``.

    python benchmarks/noise_guarantee/simulate.py smoke    # 1 incident per cell, prints counts only
    python benchmarks/noise_guarantee/simulate.py freeze   # hash protocol, script and library
    python benchmarks/noise_guarantee/simulate.py run      # the one main run (refuses a rerun)

See PROTOCOL.md. Results go to benchmarks/results/noise_guarantee/.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
import sys
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

OUTPUT = PROJECT / "benchmarks" / "results" / "noise_guarantee"
FREEZE = HERE / "FREEZE.json"
SCENARIOS = ("single", "pair", "near_threshold", "healing", "two_causes", "misdeclared", "heavy_tail")
HOLDING = SCENARIOS[:5]
SIZES = (4, 6, 8)
NOISE_RATIOS = (0.25, 0.5)
INTERVALS = ("anytime", "student_t", "normal")
INCIDENTS = 200
SMOKE_SEED_OFFSET = 10_000_000
THRESHOLD = 0.02
BASE = 0.9
ALPHA = 0.05


def cause(rng: random.Random, pool: list[str], size: int | None = None) -> frozenset[str]:
    size = size or rng.choice((1, 2))
    chosen = rng.sample(pool, size)
    for member in chosen:
        pool.remove(member)
    return frozenset(chosen)


def world(scenario: str, k: int, seed: int) -> dict[str, Any]:
    """Exact mask means for one synthetic incident."""
    rng = random.Random(f"world|{scenario}|{k}|{seed}")
    components = [f"c{i}" for i in range(k)]
    pool = components.copy()
    base_kind = scenario if scenario in HOLDING else ("single" if seed % 2 == 0 else "pair")
    causes: list[frozenset[str]] = []
    healer: str | None = None
    if base_kind == "single":
        causes.append(cause(rng, pool, 1))
        drop = rng.uniform(1.5, 4.0)
    elif base_kind == "pair":
        causes.append(cause(rng, pool, 2))
        drop = rng.uniform(1.5, 4.0)
    elif base_kind == "near_threshold":
        causes.append(cause(rng, pool))
        drop = rng.uniform(1.05, 1.3)
    elif base_kind == "healing":
        causes.append(cause(rng, pool))
        healer = rng.choice(pool)
        pool.remove(healer)
        drop = rng.uniform(1.5, 4.0)
    else:  # two_causes
        causes.append(cause(rng, pool))
        causes.append(cause(rng, pool))
        drop = rng.uniform(1.5, 4.0)
    low, high = (0.0, 0.12) if base_kind == "near_threshold" else (-0.1, 0.1)
    benign = {c: rng.uniform(low, high) * THRESHOLD for c in components}
    for group in causes:
        for member in group:
            benign[member] = 0.0
    if healer is not None:
        benign[healer] = 0.0
    return {
        "components": components,
        "causes": [sorted(c) for c in causes],
        "healer": healer,
        "drop": drop * THRESHOLD,
        "benign": benign,
    }


def true_mean(spec: dict[str, Any], mask: frozenset[str]) -> float:
    value = BASE - sum(spec["benign"][c] for c in mask)
    failing = any(set(group) <= mask for group in spec["causes"])
    if failing and (spec["healer"] is None or spec["healer"] not in mask):
        value -= spec["drop"]
    return value


def minimal_failing(spec: dict[str, Any]) -> set[frozenset[str]]:
    components = spec["components"]
    fails = {
        frozenset(mask)
        for size in range(1, len(components) + 1)
        for mask in itertools.combinations(components, size)
        if BASE - true_mean(spec, frozenset(mask)) >= THRESHOLD
    }
    return {mask for mask in fails if not any(other < mask for other in fails)}


def noise(scenario: str, sigma: float, key: str) -> float:
    rng = random.Random(key)
    if scenario == "misdeclared":
        return rng.gauss(0.0, 3 * sigma)
    if scenario == "heavy_tail":
        chi = sum(rng.gauss(0.0, 1.0) ** 2 for _ in range(3))
        return rng.gauss(0.0, 1.0) / math.sqrt(chi / 3) * sigma / math.sqrt(3)
    return rng.gauss(0.0, sigma)


def incident_for(k: int, interval: str, sigma: float) -> Incident:
    replay: dict[str, Any] = {"repeats": 3, "max_repeats": 24, "confidence": 1 - ALPHA, "interval": interval}
    if interval == "anytime":
        replay["noise_scale"] = sigma
    components = [f"c{i}" for i in range(k)]
    return Incident.from_spec(
        {
            "version": "1.0",
            "id": f"sim-k{k}",
            "good": dict.fromkeys(components, "good"),
            "bad": dict.fromkeys(components, "bad"),
            "metric": {"name": "score", "direction": "higher_is_better", "regression_threshold": THRESHOLD},
            "replay": replay,
            "search": {"max_cause_size": 2},
            "budget": {"audit": "extended"},
            "adapter": {"type": "python", "callable": "simulated:runner"},
        },
        base_dir=HERE,
    )


def one_cell(job: tuple[str, int, float, int]) -> list[dict[str, Any]]:
    scenario, k, ratio, seed = job
    sigma = ratio * THRESHOLD
    spec = world(scenario, k, seed)
    accepted = minimal_failing(spec)

    def runner(state: dict[str, Any], _cases: Any, _metric: str, seed: int = 0) -> float:
        mask = frozenset(c for c, value in state.items() if value == "bad")
        key = f"noise|{scenario}|{k}|{ratio}|{job[3]}|{sorted(mask)}|{seed}"
        return true_mean(spec, mask) + noise(scenario, sigma, key)

    rows = []
    for interval in INTERVALS:
        incident = incident_for(k, interval, sigma)
        for strategy in STRATEGIES:
            report = investigate(incident, budget=2**k, strategy=strategy, seed=0, executor=runner)
            diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
            correct = diagnosis in accepted if diagnosis is not None else False
            check = report.confidence_meta.get("noise_check") or {}
            rows.append(
                {
                    "scenario": scenario,
                    "k": k,
                    "noise_ratio": ratio,
                    "incident": seed,
                    "interval": interval,
                    "strategy": strategy,
                    "status": report.status,
                    "diagnosis": sorted(diagnosis) if diagnosis is not None else None,
                    "accepted": sorted(sorted(a) for a in accepted),
                    "wrong_verified": int(report.status == "verified" and not correct),
                    "correct_verified": int(report.status == "verified" and correct),
                    "noise_check": check.get("status"),
                    "runs": report.total_runs,
                    "replays": report.experiments_used,
                }
            )
    return rows


def jobs(offset: int, count: int) -> list[tuple[str, int, float, int]]:
    return [
        (scenario, k, ratio, offset + i)
        for scenario in SCENARIOS
        for k in SIZES
        for ratio in NOISE_RATIOS
        for i in range(count)
    ]


def clopper_pearson_upper(failures: int, trials: int, level: float = 0.95) -> float:
    """One-sided upper bound, by bisection on the binomial tail (computed in log space)."""
    if failures >= trials:
        return 1.0

    def tail(p: float) -> float:
        logs = [
            math.lgamma(trials + 1)
            - math.lgamma(i + 1)
            - math.lgamma(trials - i + 1)
            + i * math.log(p)
            + (trials - i) * math.log1p(-p)
            for i in range(failures + 1)
        ]
        peak = max(logs)
        return math.exp(peak) * sum(math.exp(value - peak) for value in logs)

    low, high = failures / trials, 1.0
    for _ in range(100):
        middle = (low + high) / 2
        if 0 < middle < 1 and tail(middle) > 1 - level:
            low = middle
        else:
            high = middle
    return high


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["scenario"], row["interval"], row["strategy"])].append(row)
        holding = "assumptions_hold" if row["scenario"] in HOLDING else "assumptions_violated"
        groups[(holding, row["interval"], row["strategy"])].append(row)
    table = []
    for (scenario, interval, strategy), values in sorted(groups.items()):
        n = len(values)
        wrong = sum(v["wrong_verified"] for v in values)
        table.append(
            {
                "scenario": scenario,
                "interval": interval,
                "strategy": strategy,
                "investigations": n,
                "wrong_verified": wrong,
                "wrong_verified_rate": wrong / n,
                "wrong_verified_upper95": clopper_pearson_upper(wrong, n),
                "correct_verified_rate": sum(v["correct_verified"] for v in values) / n,
                "status_rates": {
                    status: sum(v["status"] == status for v in values) / n
                    for status in sorted({v["status"] for v in values})
                },
                "noise_check_violated_rate": sum(v["noise_check"] == "violated" for v in values) / n,
                "mean_runs": statistics.fmean(v["runs"] for v in values),
            }
        )
    primary = [
        row
        for row in table
        if row["interval"] == "anytime"
        and (
            row["scenario"] == "assumptions_hold"
            or (row["scenario"] in HOLDING and row["strategy"] == "adaptive")
        )
    ]
    supported = all(
        r["wrong_verified_rate"] <= ALPHA and r["wrong_verified_upper95"] <= ALPHA for r in primary
    )
    return {"alpha": ALPHA, "primary_supported": supported, "primary": primary, "table": table}


def report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Noise-guarantee simulation (pre-registered, one run)",
        "",
        "Protocol: [PROTOCOL.md](../../noise_guarantee/PROTOCOL.md). Claim: with `interval: anytime`, "
        "P(verified and not a true minimal failing set) <= 0.05 when the noise assumptions hold.",
        "",
        f"**Primary claim supported: {'yes' if summary['primary_supported'] else 'NO'}.**",
        "",
        "## Wrong verified, pooled over the five assumption-holding scenarios",
        "",
        "| interval | strategy | investigations | wrong verified | rate | 95% upper | correct verified | mean runs |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scope in ("assumptions_hold", "assumptions_violated"):
        if scope == "assumptions_violated":
            lines += [
                "",
                "## Wrong verified when the noise assumption is violated (pooled)",
                "",
                "| interval | strategy | investigations | wrong verified | rate | 95% upper | correct verified | mean runs |",
                "|---|---|---:|---:|---:|---:|---:|---:|",
            ]
        for row in summary["table"]:
            if row["scenario"] == scope:
                lines.append(
                    f"| {row['interval']} | {row['strategy']} | {row['investigations']} | "
                    f"**{row['wrong_verified']}** | {row['wrong_verified_rate']:.4f} | "
                    f"{row['wrong_verified_upper95']:.4f} | {row['correct_verified_rate']:.3f} | "
                    f"{row['mean_runs']:.1f} |"
                )
    lines += [
        "",
        "## Per scenario (adaptive)",
        "",
        "| scenario | interval | wrong verified | rate | 95% upper | correct verified | statuses | noise check violated | mean runs |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in summary["table"]:
        if row["strategy"] == "adaptive" and row["scenario"] in SCENARIOS:
            statuses = ", ".join(f"{k} {v:.2f}" for k, v in row["status_rates"].items())
            lines.append(
                f"| {row['scenario']} | {row['interval']} | **{row['wrong_verified']}** | "
                f"{row['wrong_verified_rate']:.4f} | {row['wrong_verified_upper95']:.4f} | "
                f"{row['correct_verified_rate']:.3f} | {statuses} | "
                f"{row['noise_check_violated_rate']:.3f} | {row['mean_runs']:.1f} |"
            )
    lines += [
        "",
        "Investigations of one incident share noise draws across intervals and strategies, so",
        "rows are paired and not independent across strategies. All rows: `rows.json`.",
        "",
    ]
    return "\n".join(lines)


def frozen_files() -> dict[str, str]:
    files = [HERE / "PROTOCOL.md", HERE / "simulate.py"]
    files += sorted(
        p
        for p in (PROJECT / "src" / "regressleuth").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    return {str(p.relative_to(PROJECT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "smoke":
        work = jobs(SMOKE_SEED_OFFSET, 1)
        with ProcessPoolExecutor() as pool:
            rows = [row for cell in pool.map(one_cell, work) for row in cell]
        report_markdown(summarize(rows))  # exercised, not shown: outcomes stay unseen before the run
        print(f"smoke: {len(rows)} investigations completed")
        return 0
    if mode == "freeze":
        if FREEZE.exists():
            print("already frozen", file=sys.stderr)
            return 3
        FREEZE.write_text(
            json.dumps(
                {
                    "frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "files": frozen_files(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print(f"froze {len(frozen_files())} files")
        return 0
    if mode != "run":
        print(__doc__, file=sys.stderr)
        return 2
    if (OUTPUT / "rows.json").exists():
        print("refusing to overwrite the existing main run", file=sys.stderr)
        return 3
    frozen = json.loads(FREEZE.read_text())["files"]
    if frozen != frozen_files():
        changed = sorted(
            set(frozen) ^ set(frozen_files()) | {k for k in frozen if frozen_files().get(k) != frozen[k]}
        )
        print(f"freeze broken: {changed}", file=sys.stderr)
        return 1
    started = datetime.now(timezone.utc)
    with ProcessPoolExecutor() as pool:
        rows = [row for cell in pool.map(one_cell, jobs(0, INCIDENTS), chunksize=8) for row in cell]
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
