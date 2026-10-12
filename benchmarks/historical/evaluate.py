"""Evaluate the sealed historical suite using frozen Regressleuth public APIs.

This file is distinct from the published development and holdout evaluators.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from harness import load_candidates, validate_evidence, verify_freeze, verify_seal

from regressleuth import Incident, investigate
from regressleuth.errors import IncompatibleReplay, ReplayError
from regressleuth.strategies import STRATEGIES

BUDGETS: tuple[int | str, ...] = (4, 6, 8, 12, "full")
RANDOM_SEEDS = 10
OUTPUT = PROJECT / "benchmarks" / "results" / "historical"


def table_lookup(incident: Incident, table: dict[str, list[dict[str, Any]]]) -> Any:
    """Every strategy reads the same immutable mask/seed observation table."""

    def replay(state: dict[str, Any], _cases: Any, _metric: str, seed: int = 0) -> float:
        key = "|".join(c for c in incident.changed_components if state[c] == incident.bad[c])
        outcome = table[key][seed]
        status = outcome["status"]
        if status == "incompatible":
            raise IncompatibleReplay("historical hybrid was infeasible")
        if status == "error":
            raise ReplayError("historical replay failed", kind=outcome.get("error_kind") or "error")
        if status != "ok":
            raise ValueError(f"unexpected stored status: {status}")
        return float(outcome["metric"])

    return replay


def replay_wall(report: Any, table: dict[str, list[dict[str, Any]]]) -> float:
    return sum(
        sum(entry["seconds"] for entry in table["|".join(experiment.changed)][: experiment.runs])
        for experiment in report.experiments
    )


def evaluate_one(
    incident: Incident,
    table: dict[str, list[dict[str, Any]]],
    accepted: set[frozenset[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    before = hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest()
    space = 1 << len(incident.changed_components)
    for strategy in STRATEGIES:
        for budget in BUDGETS:
            limit = space if budget == "full" else int(budget)
            for seed in range(RANDOM_SEEDS) if strategy == "random" else range(1):
                report = investigate(
                    incident,
                    budget=limit,
                    strategy=strategy,
                    seed=seed,
                    audit="extended",
                    executor=table_lookup(incident, table),
                )
                diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
                correct = diagnosis in accepted if diagnosis is not None else False
                rows.append(
                    {
                        "suite": "historical_external",
                        "incident": incident.id,
                        "components": len(incident.changed_components),
                        "search_space": space,
                        "budget": budget,
                        "budget_above_space": budget != "full" and limit > space,
                        "strategy": strategy,
                        "strategy_label": "exhaustive_order"
                        if strategy == "exhaustive" and limit < space
                        else strategy,
                        "random_seed": seed if strategy == "random" else None,
                        "audit": "extended",
                        "interval": incident.replay.interval,
                        "status": report.status,
                        "diagnosis": sorted(diagnosis) if diagnosis is not None else None,
                        "verified_correct": int(report.status == "verified" and correct),
                        "verified_wrong": int(report.status == "verified" and not correct),
                        "inferred_correct": int(report.status == "inferred" and correct),
                        "false_attribution": int(diagnosis is not None and not correct),
                        "isolation_replays": report.isolation_replays,
                        "audit_replays": int(report.audit.get("extra_replays", 0)),
                        "total_replays": report.experiments_used,
                        "runner_runs": report.total_runs,
                        "replay_wall_seconds": replay_wall(report, table),
                    }
                )
    after = hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest()
    if before != after:
        raise RuntimeError(f"strategy evaluation mutated shared observations for {incident.id}")
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["strategy"], str(row["budget"]))].append(row)
    summary = []
    for strategy in STRATEGIES:
        for budget in BUDGETS:
            values = grouped.get((strategy, str(budget)), [])
            if not values:
                continue
            summary.append(
                {
                    "strategy": strategy,
                    "budget": budget,
                    "incidents": len({row["incident"] for row in values}),
                    "runs": len(values),
                    "verified_correct": sum(row["verified_correct"] for row in values),
                    "verified_wrong": sum(row["verified_wrong"] for row in values),
                    "inferred_correct": sum(row["inferred_correct"] for row in values),
                    "unresolved": sum(row["status"] == "unresolved" for row in values),
                    "inconclusive": sum(row["status"] == "inconclusive" for row in values),
                    "assumption_violated": sum(row["status"] == "assumption_violated" for row in values),
                    "false_attribution": sum(row["false_attribution"] for row in values),
                    "mean_isolation_replays": statistics.fmean(row["isolation_replays"] for row in values),
                    "mean_audit_replays": statistics.fmean(row["audit_replays"] for row in values),
                    "mean_total_replays": statistics.fmean(row["total_replays"] for row in values),
                    "mean_replay_wall_seconds": statistics.fmean(
                        row["replay_wall_seconds"] for row in values
                    ),
                }
            )
    return summary


def funnel(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Every logged candidate, by stage. Excluded = failed the predeclared eligibility rules;
    disputed = looked eligible but controlled reproduction did not support the report."""
    reasons: dict[str, int] = defaultdict(int)
    for row in candidates:
        if row["status"] == "excluded":
            for reason in row["exclusion_reasons"]:
                reasons[reason] += 1
    return {
        "logged": len(candidates),
        "excluded": sum(row["status"] == "excluded" for row in candidates),
        "excluded_by_reason": dict(sorted(reasons.items())),
        "sent_to_reproduction": sum(row["status"] in {"included", "disputed"} for row in candidates),
        "disputed": [row["incident_id"] for row in candidates if row["status"] == "disputed"],
        "included": [row["incident_id"] for row in candidates if row["status"] == "included"],
        "unscreened": [row["incident_id"] for row in candidates if row["status"] == "candidate"],
    }


def funnel_markdown(flow: dict[str, Any]) -> list[str]:
    lines = [
        "## Candidate funnel (all logged candidates)",
        "",
        f"- Logged before any reproduction: **{flow['logged']}**",
        f"- Excluded by the predeclared eligibility rules: **{flow['excluded']}** "
        + ", ".join(f"{reason} {count}" for reason, count in flow["excluded_by_reason"].items()),
        f"- Sent to controlled reproduction: **{flow['sent_to_reproduction']}**",
        f"- Disputed (reproduction did not support the report; kept, excluded from accuracy): "
        f"**{len(flow['disputed'])}** {', '.join(flow['disputed']) or ''}",
        f"- Included, independently reproduced and sealed: **{len(flow['included'])}**",
        f"- Still unscreened: **{len(flow['unscreened'])}**",
        "",
    ]
    return lines


def safety_markdown(summary: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## Outcomes per strategy (wrong verified first)",
        "",
        "| strategy | budget | WRONG verified | correct verified | correct inferred | unresolved "
        "| inconclusive | assumption violated | runs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['strategy']} | {row['budget']} | **{row['verified_wrong']}** | {row['verified_correct']} | "
            f"{row['inferred_correct']} | {row['unresolved']} | {row['inconclusive']} | "
            f"{row['assumption_violated']} | {row['runs']} |"
        )
    wrong = sum(row["verified_wrong"] for row in summary)
    lines += ["", f"Total wrong `verified` diagnoses across all strategy-budget-seed runs: **{wrong}**.", ""]
    return lines


def report_markdown(
    rows: list[dict[str, Any]], summary: list[dict[str, Any]], flow: dict[str, Any] | None = None
) -> str:
    incidents = sorted({row["incident"] for row in rows})
    sizes: dict[int, int] = defaultdict(int)
    for components in {row["incident"]: row["components"] for row in rows}.values():
        sizes[components] += 1
    lines = [
        "# Historical external incident pilot",
        "",
        "This evaluation is separate from the frozen development and holdout benchmarks.",
        "It uses the sealed, source-derived observation tables; all six strategies share",
        "the same observations, `extended` audit, and Student-t default. Results are",
        "descriptive. A one-component incident has only two states and does not show a",
        "search advantage.",
        "",
        f"Included incidents: {len(incidents)}. Full per-run data: `rows.json`.",
        "",
        "Changed components per incident (cause-size strata are reported separately): "
        + ", ".join(f"{size}: {count}" for size, count in sorted(sizes.items()))
        + ". Budgets above an incident's search space are marked in `rows.json`.",
        "",
        *(funnel_markdown(flow) if flow is not None else []),
        *safety_markdown(summary),
        "## All metrics",
        "",
        "| strategy | budget | incidents | runs | correct verified | false verified | correct inferred | unresolved | inconclusive | assumption violated | mean isolation | mean audit | mean total | mean replay wall s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['strategy']} | {row['budget']} | {row['incidents']} | {row['runs']} | "
            f"{row['verified_correct']} | {row['verified_wrong']} | {row['inferred_correct']} | "
            f"{row['unresolved']} | {row['inconclusive']} | {row['assumption_violated']} | "
            f"{row['mean_isolation_replays']:.2f} | {row['mean_audit_replays']:.2f} | "
            f"{row['mean_total_replays']:.2f} | {row['mean_replay_wall_seconds']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Per-incident full-budget results",
            "",
            "| incident | components | space | strategy | status | diagnosis | false verified | total replays | replay wall s |",
            "|---|---:|---:|---|---|---|---:|---:|---:|",
        ]
    )
    for row in rows:
        if row["budget"] != "full" or row["random_seed"] not in (None, 0):
            continue
        lines.append(
            f"| {row['incident']} | {row['components']} | {row['search_space']} | "
            f"{row['strategy']} | {row['status']} | {row['diagnosis']} | "
            f"{row['verified_wrong']} | {row['total_replays']} | {row['replay_wall_seconds']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The displayed 0.95 Student-t setting, where applied, is an interval setting for",
            "individual replay comparisons. It is not a confidence bound for the diagnosis.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    if (OUTPUT / "rows.json").exists():
        # One-time evaluation: results of the sealed suite are never silently replaced.
        print(
            f"refusing to overwrite the existing evaluation in {OUTPUT}; a new evaluation must be "
            "a new, separately documented benchmark version",
            file=sys.stderr,
        )
        return 3
    verify_freeze()
    verify_seal()
    validate_evidence()
    included = [row for row in load_candidates() if row["status"] == "included"]
    if not included:
        raise ValueError("no eligible sealed historical incidents")
    rows: list[dict[str, Any]] = []
    for item in included:
        folder = HERE / "incidents" / item["incident_id"]
        incident = Incident.from_file(folder / "incident.yaml")
        if incident.id != item["incident_id"] or incident.replay.interval != "student_t":
            raise ValueError(f"incident profile disagrees with candidate record: {item['incident_id']}")
        table = json.loads((folder / "replay_table.json").read_text(encoding="utf-8"))["table"]
        truth = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
        accepted = {frozenset(cause) for cause in truth["accepted_causes"]}
        rows.extend(evaluate_one(incident, table, accepted))
    summary = summarize(rows)
    flow = funnel(load_candidates())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    seal_hash = hashlib.sha256((HERE / "SEAL.json").read_bytes()).hexdigest()
    (OUTPUT / "RUN.json").write_text(
        json.dumps(
            {
                "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "seal_sha256": seal_hash,
                "source_tree_sha256": json.loads((HERE / "FREEZE_MANIFEST.json").read_text())[
                    "source_tree_sha256"
                ],
                "strategies": list(STRATEGIES),
                "budgets": list(BUDGETS),
                "random_seeds": RANDOM_SEEDS,
                "audit": "extended",
                "interval": "student_t",
                "funnel": flow,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "rows.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTPUT / "EVALUATION.md").write_text(report_markdown(rows, summary, flow), encoding="utf-8")
    print(f"wrote {len(rows)} separate strategy-budget-seed rows for {len(included)} incidents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
