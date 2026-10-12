"""Compare search strategies on the real-model incidents (and check the real controls).

Every runner is executed once per (component mask, run seed) and the raw table is
stored in benchmarks/results/tables/. Every strategy then replays against that exact
table, so all strategies see identical metrics, identical noise and identical
incompatibilities. Results equal live runs while each model is evaluated only once.

Usage: python benchmarks/run_real.py [incident-prefix ...]
Run it with an interpreter that has the demos' dependencies (see the README).
"""

from __future__ import annotations

import itertools
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))

from regressleuth import Incident, investigate
from regressleuth.errors import IncompatibleReplay
from regressleuth.executor import CommandExecutor
from regressleuth.strategies import STRATEGIES

BUDGETS = (4, 6, 8, 12, 16, 32)
RANDOM_SEEDS = 10
TABLES = ROOT / "results" / "tables"


def build_table(incident: Incident, workers: int) -> dict[str, list[dict[str, Any]]]:
    """metric (or None when incompatible) and wall seconds for every mask and run seed."""
    path = TABLES / f"{incident.id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["table"]
    executor = CommandExecutor(incident)
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
        started = time.perf_counter()
        try:
            value: float | None = executor(
                incident.selected_state(mask), incident.replay.cases, incident.replay.metric, seed=seed
            )
        except IncompatibleReplay:
            value = None
        return {"metric": value, "seconds": time.perf_counter() - started}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, jobs))
    table: dict[str, list[dict[str, Any]]] = {}
    for (mask, _seed), result in zip(jobs, results, strict=True):
        table.setdefault("|".join(sorted(mask)), []).append(result)
    TABLES.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"incident": incident.id, "table": table}), encoding="utf-8")
    return table


def make_lookup(incident: Incident, table: dict[str, list[dict[str, Any]]]) -> Any:
    def lookup(state: dict[str, Any], _cases: Path, _metric: str, seed: int = 0) -> float:
        mask = "|".join(sorted(c for c in incident.changed_components if state[c] == incident.bad[c]))
        entry = table[mask][seed]
        if entry["metric"] is None:
            raise IncompatibleReplay("hybrid is incompatible")
        return float(entry["metric"])

    return lookup


def wall_seconds(report: Any, table: dict[str, list[dict[str, Any]]]) -> float:
    return sum(
        sum(item["seconds"] for item in table["|".join(e.changed)][: e.runs]) for e in report.experiments
    )


def main(prefixes: tuple[str, ...]) -> None:
    truth = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for path in sorted((ROOT / "incidents").glob("*.json")):
        if prefixes and not path.stem.startswith(prefixes):
            continue
        incident = Incident.from_file(path)
        incident = replace(
            incident,
            replay=replace(incident.replay, interval="normal"),
            search=replace(incident.search, audit="full"),
        )
        cause = frozenset(truth[incident.id])
        table = build_table(incident, workers=2 if path.stem.startswith("text_") else 8)
        lookup = make_lookup(incident, table)
        for strategy in STRATEGIES:
            for budget in BUDGETS:
                seeds = range(RANDOM_SEEDS) if strategy == "random" else range(1)
                reports = [
                    investigate(incident, budget=budget, strategy=strategy, executor=lookup, seed=s)
                    for s in seeds
                ]
                rows.append(
                    {
                        "incident": incident.id,
                        "family": incident.id.split("_")[0],
                        "components": len(incident.changed_components),
                        "cause_size": len(cause),
                        "noisy": incident.replay.max_repeats > 1,
                        "strategy": strategy,
                        "budget": budget,
                        "exact": statistics.fmean(
                            r.status == "verified" and frozenset(r.diagnosis or ()) == cause for r in reports
                        ),
                        "exact_any": statistics.fmean(frozenset(r.diagnosis or ()) == cause for r in reports),
                        "wrong_verified": statistics.fmean(
                            r.status == "verified" and frozenset(r.diagnosis or ()) != cause for r in reports
                        ),
                        "isolation_replays": statistics.fmean(r.isolation_replays for r in reports),
                        "total_replays": statistics.fmean(r.experiments_used for r in reports),
                        "runs": statistics.fmean(r.total_runs for r in reports),
                        "wall_seconds": statistics.fmean(wall_seconds(r, table) for r in reports),
                    }
                )
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "real_incidents.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "real_incidents.md").write_text(render(rows), encoding="utf-8")
    run_controls(prefixes)
    print(render(rows))


def run_controls(prefixes: tuple[str, ...]) -> None:
    expected = json.loads((ROOT / "controls" / "expected_status.json").read_text(encoding="utf-8"))
    lines = [
        "# Real-model controls",
        "",
        "| control | expected | " + " | ".join(STRATEGIES) + " |",
        "|---|---|" + "---|" * len(STRATEGIES),
    ]
    for name, status in sorted(expected.items()):
        if prefixes and not name.startswith(prefixes):
            continue
        incident = Incident.from_file(ROOT / "controls" / f"{name}.json")
        incident = replace(
            incident,
            replay=replace(incident.replay, interval="normal"),
            search=replace(incident.search, audit="full"),
        )
        cells = []
        for strategy in STRATEGIES:
            report = investigate(incident, budget=32, strategy=strategy, executor=None)
            accepted = {status} | ({"unresolved"} if strategy == "one_factor" else set())
            cells.append(("ok " if report.status in accepted else "MISMATCH ") + report.status)
        lines.append(f"| {name} | {status} | " + " | ".join(cells) + " |")
    (ROOT / "results" / "real_controls.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render(rows: list[dict[str, Any]]) -> str:
    def pick(**match: Any) -> list[dict[str, Any]]:
        return [r for r in rows if all(r[k] == v for k, v in match.items())]

    incidents = list(dict.fromkeys(r["incident"] for r in rows))
    lines = [
        "# Real-model incident results",
        "",
        (
            f"{len(incidents)} incidents. Verified & right = status verified and equal to the "
            "injected cause; right at any status also counts inferred results. Random is "
            f"averaged over {RANDOM_SEEDS} seeds. Budgets count endpoint, search and verification "
            "replays (isolation); the audit adds replays on top (total). Wall time is the summed "
            "runner time of the replays used."
        ),
        "",
    ]
    for budget in (8, 16, 32):
        lines += [
            f"## Summary at budget {budget}",
            "",
            (
                "| strategy | verified & right | pair verified & right | right at any status "
                "| wrong verified | isolation replays | total replays | runner runs | wall s |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for strategy in STRATEGIES:
            sel = pick(strategy=strategy, budget=budget)
            pair = [r for r in sel if r["cause_size"] == 2]
            lines.append(
                f"| {strategy} | {statistics.fmean(r['exact'] for r in sel):.2f} | "
                f"{statistics.fmean(r['exact'] for r in pair):.2f} | "
                f"{statistics.fmean(r['exact_any'] for r in sel):.2f} | "
                f"{statistics.fmean(r['wrong_verified'] for r in sel):.2f} | "
                f"{statistics.fmean(r['isolation_replays'] for r in sel):.1f} | "
                f"{statistics.fmean(r['total_replays'] for r in sel):.1f} | "
                f"{statistics.fmean(r['runs'] for r in sel):.0f} | "
                f"{statistics.fmean(r['wall_seconds'] for r in sel):.1f} |"
            )
        lines.append("")
    lines += [
        "## Per incident at budget 16",
        "",
        "Cell: exact (isolation replays). 1.0 = verified the right cause; 0.0 = not verified.",
        "",
        "| incident | k | cause | " + " | ".join(STRATEGIES) + " |",
        "|---|---:|---:|" + "---:|" * len(STRATEGIES),
    ]
    for incident in incidents:
        cells = []
        for strategy in STRATEGIES:
            r = pick(incident=incident, strategy=strategy, budget=16)[0]
            cells.append(f"{r['exact']:.1f} ({r['isolation_replays']:.1f})")
        first = pick(incident=incident, strategy="adaptive", budget=16)[0]
        lines.append(
            f"| {incident} | {first['components']} | {first['cause_size']} | " + " | ".join(cells) + " |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main(tuple(sys.argv[1:]))
