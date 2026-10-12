"""Evaluate the sealed dependency-drift suite once (see SELECTION_PROTOCOL.md).

All six strategies read the same sealed replay tables. The evaluator refuses to run if
results already exist, if the seal or the method freeze changed, or if evidence is
incomplete. It reports the funnel, wrong ``verified`` first, and the three
pre-registered decisions.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(HERE))

from harness import load_candidates, validate_evidence, verify_freeze, verify_seal

from regressleuth import Incident, investigate
from regressleuth.errors import IncompatibleReplay, ReplayError
from regressleuth.strategies import STRATEGIES

BUDGETS: tuple[int | str, ...] = (4, 6, 8, 12, 16, 24, 32, "full")
RANDOM_SEEDS = 10
OUTPUT = PROJECT / "benchmarks" / "results" / "drift"


def table_lookup(table: dict[str, list[dict[str, Any]]]) -> Any:
    def replay(state: dict[str, Any], *_args: Any, **_kwargs: Any) -> float:
        mask = sorted(name for name, value in state.items() if value == state_bad[name])
        outcome = table["|".join(mask)][0]
        if outcome["status"] == "incompatible":
            raise IncompatibleReplay("the hybrid could not be installed")
        if outcome["status"] != "ok":
            raise ReplayError("stored replay failed", kind=outcome.get("error_kind") or "error")
        return float(outcome["metric"])

    state_bad: dict[str, Any] = {}
    replay.bind = state_bad.update  # type: ignore[attr-defined]
    return replay


def stratum(k: int) -> str:
    return "1" if k == 1 else "2-4" if k <= 4 else "5-7" if k <= 7 else "8-12"


def evaluate_one(incident: Incident, table: dict[str, Any], truth: dict[str, Any]) -> list[dict[str, Any]]:
    accepted = {frozenset(cause) for cause in truth["accepted_causes"]}
    coupled = {frozenset(cause) for cause in truth.get("coupled_minimal", [])}
    k = len(incident.changed_components)
    space = 2**k
    before = hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest()
    sizes = sorted({len(cause) for cause in accepted})
    rows = []
    for strategy in STRATEGIES:
        for budget in BUDGETS:
            limit = space if budget == "full" else int(budget)
            for seed in range(RANDOM_SEEDS) if strategy == "random" else range(1):
                lookup = table_lookup(table)
                lookup.bind(incident.bad)
                report = investigate(
                    incident, budget=limit, strategy=strategy, seed=seed, audit="extended", executor=lookup
                )
                diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
                correct = diagnosis in accepted if diagnosis is not None else False
                rows.append(
                    {
                        "incident": incident.id,
                        "k": k,
                        "stratum": stratum(k),
                        "cause_sizes": sizes,
                        "coupled": bool(coupled),
                        "search_space": space,
                        "budget": budget,
                        "budget_above_space": budget != "full" and limit > space,
                        "strategy": strategy,
                        "random_seed": seed if strategy == "random" else None,
                        "status": report.status,
                        "diagnosis": sorted(diagnosis) if diagnosis is not None else None,
                        "verified_correct": int(report.status == "verified" and correct),
                        "verified_wrong": int(report.status == "verified" and not correct),
                        "inferred_correct": int(report.status == "inferred" and correct),
                        "isolation_replays": report.isolation_replays,
                        "total_replays": report.experiments_used,
                    }
                )
    if hashlib.sha256(json.dumps(table, sort_keys=True).encode()).hexdigest() != before:
        raise RuntimeError(f"evaluation mutated the stored table of {incident.id}")
    return rows


def sign_test(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(wins, losses) + 1)) / 2**n)


def paired(rows: list[dict[str, Any]], budget: str) -> dict[str, Any]:
    """Adaptive vs ddmin, isolation replays before a correct verified (never = worst)."""
    by = {
        (r["incident"], r["strategy"]): r
        for r in rows
        if str(r["budget"]) == budget and r["random_seed"] in (None,)
    }
    wins = losses = ties = 0
    details = []
    for incident in sorted({r["incident"] for r in rows if r["k"] >= 3}):
        a, d = by[(incident, "adaptive")], by[(incident, "ddmin")]
        cost_a = a["isolation_replays"] if a["verified_correct"] else math.inf
        cost_d = d["isolation_replays"] if d["verified_correct"] else math.inf
        outcome = "adaptive" if cost_a < cost_d else "ddmin" if cost_d < cost_a else "tie"
        wins += outcome == "adaptive"
        losses += outcome == "ddmin"
        ties += outcome == "tie"
        details.append({"incident": incident, "adaptive": cost_a, "ddmin": cost_d, "fewer": outcome})
    p = sign_test(wins, losses)
    return {
        "budget": budget,
        "adaptive_wins": wins,
        "ddmin_wins": losses,
        "ties": ties,
        "sign_test_p": p,
        "claim_supported": wins > losses and p < 0.05,
        "incidents": details,
    }


def funnel(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: dict[str, int] = defaultdict(int)
    for row in candidates:
        for reason in row.get("exclusion_reasons", []):
            reasons[reason] += 1
    return {
        "logged": len(candidates),
        "excluded": sum(r["status"] == "excluded" for r in candidates),
        "excluded_by_reason": dict(sorted(reasons.items())),
        "replayed": sum(r["status"] in {"included", "disputed"} for r in candidates),
        "disputed": [r["incident_id"] for r in candidates if r["status"] == "disputed"],
        "disputed_reasons": {
            r["incident_id"]: r.get("replay_explanation")
            or r.get("screening_notes", "").split(" Replay: ")[-1]
            for r in candidates
            if r["status"] == "disputed"
        },
        "included": [r["incident_id"] for r in candidates if r["status"] == "included"],
    }


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["strategy"], str(row["budget"]))].append(row)
    out = []
    for strategy in STRATEGIES:
        for budget in BUDGETS:
            values = groups.get((strategy, str(budget)), [])
            if values:
                out.append(
                    {
                        "strategy": strategy,
                        "budget": budget,
                        "runs": len(values),
                        "verified_wrong": sum(v["verified_wrong"] for v in values),
                        "verified_correct": sum(v["verified_correct"] for v in values),
                        "inferred_correct": sum(v["inferred_correct"] for v in values),
                        "unresolved": sum(v["status"] == "unresolved" for v in values),
                        "inconclusive": sum(v["status"] == "inconclusive" for v in values),
                        "assumption_violated": sum(v["status"] == "assumption_violated" for v in values),
                        "evaluation_error": sum(v["status"] == "evaluation_error" for v in values),
                        "mean_isolation": statistics.fmean(v["isolation_replays"] for v in values),
                        "mean_total": statistics.fmean(v["total_replays"] for v in values),
                    }
                )
    return out


def report_markdown(
    flow: dict[str, Any], summary: list[dict[str, Any]], decisions: dict[str, Any], rows: list[dict[str, Any]]
) -> str:
    lines = [
        "# Dependency-drift suite (sealed, evaluated once)",
        "",
        "Protocol: [SELECTION_PROTOCOL.md](../../drift/SELECTION_PROTOCOL.md) with addenda A and B.",
        "",
        "## Funnel",
        "",
        f"- Logged: **{flow['logged']}**; excluded: **{flow['excluded']}** ("
        + ", ".join(f"{k} {v}" for k, v in flow["excluded_by_reason"].items())
        + ")",
        f"- Replayed: **{flow['replayed']}**; disputed: **{len(flow['disputed'])}** "
        f"({', '.join(flow['disputed']) or 'none'}); included and sealed: **{len(flow['included'])}** "
        f"({', '.join(flow['included']) or 'none'})",
        "",
        *(
            ["Why each replayed candidate was disputed (from its controlled replay):", ""]
            + [f"- `{key}`: {value}" for key, value in flow.get("disputed_reasons", {}).items()]
            + [""]
            if flow.get("disputed_reasons")
            else []
        ),
        "## Pre-registered decisions",
        "",
    ]
    if not decisions["search_advantage"]:
        lines.append(
            "- Search advantage: **not supported**: no included incident has three or more changed "
            "components, so the pre-registered paired comparison has no incidents to compare"
        )
    for budget, result in decisions["search_advantage"].items():
        lines.append(
            f"- Search advantage, budget {budget}: adaptive fewer replays on {result['adaptive_wins']}, "
            f"ddmin on {result['ddmin_wins']}, ties {result['ties']}; sign test p = {result['sign_test_p']:.3g}; "
            f"claim {'SUPPORTED' if result['claim_supported'] else 'not supported'}"
            + (" (primary)" if budget == "full" else " (secondary)")
        )
    lines += [
        f"- Interaction evidence: **{'established' if decisions['interaction']['established'] else 'not established'}** "
        f"({decisions['interaction']['detail']})",
        f"- Large search spaces (k >= 8): {decisions['large_space']}",
        "",
        "## Outcomes per strategy (wrong verified first)",
        "",
        "| strategy | budget | WRONG verified | correct verified | correct inferred | unresolved | inconclusive | assumption violated | errors | mean isolation | mean total | runs |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        lines.append(
            f"| {r['strategy']} | {r['budget']} | **{r['verified_wrong']}** | {r['verified_correct']} | "
            f"{r['inferred_correct']} | {r['unresolved']} | {r['inconclusive']} | {r['assumption_violated']} | "
            f"{r['evaluation_error']} | {r['mean_isolation']:.2f} | {r['mean_total']:.2f} | {r['runs']} |"
        )
    lines += [
        "",
        "## Per incident, full budget",
        "",
        "| incident | k | stratum | cause sizes | coupled | strategy | status | diagnosis | isolation | total |",
        "|---|---:|---|---|---|---|---|---|---:|---:|",
    ]
    for r in rows:
        if r["budget"] == "full" and r["random_seed"] in (None, 0):
            lines.append(
                f"| {r['incident']} | {r['k']} | {r['stratum']} | {r['cause_sizes']} | {r['coupled']} | {r['strategy']} | "
                f"{r['status']} | {r['diagnosis']} | {r['isolation_replays']} | {r['total_replays']} |"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if any((OUTPUT / name).exists() for name in ("RUN.json", "rows.json", "summary.json", "EVALUATION.md")):
        print(f"refusing to overwrite the existing evaluation in {OUTPUT}", file=sys.stderr)
        return 3
    verify_freeze()
    verify_seal()
    validate_evidence()
    candidates = load_candidates()
    included = [row for row in candidates if row["status"] == "included"]
    rows: list[dict[str, Any]] = []
    for item in included:
        folder = HERE / "incidents" / item["incident_id"]
        incident = Incident.from_file(folder / "incident.yaml")
        table = json.loads((folder / "replay_table.json").read_text(encoding="utf-8"))["table"]
        truth = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
        rows.extend(evaluate_one(incident, table, truth))
    flow = funnel(candidates)
    multi = [r for r in rows if r["k"] >= 3]
    decisions: dict[str, Any] = {
        "search_advantage": {b: paired(multi, b) for b in ("full", "8", "12")} if multi else {},
    }
    interaction_hits = sorted(
        {
            r["incident"]
            for r in rows
            if r["budget"] == "full" and r["verified_correct"] and r["diagnosis"] and len(r["diagnosis"]) >= 2
        }
    )
    with_pairs = sorted({r["incident"] for r in rows if any(size >= 2 for size in r["cause_sizes"])})
    decisions["interaction"] = {
        "established": bool(interaction_hits),
        "detail": f"incidents with a minimal cause of two or more components: {with_pairs or 'none'}; "
        f"verified correctly at full budget by at least one strategy: {interaction_hits or 'none'}",
    }
    large = sorted({r["incident"] for r in rows if r["k"] >= 8})
    decisions["large_space"] = f"{len(large)} incident(s) with k >= 8 ({', '.join(large) or 'none'}); " + (
        "described per incident, not summarized as a rate" if len(large) < 3 else "see the per-incident table"
    )
    summary = summarize(rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "RUN.json").write_text(
        json.dumps(
            {
                "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "seal_sha256": hashlib.sha256((HERE / "SEAL.json").read_bytes()).hexdigest(),
                "strategies": list(STRATEGIES),
                "budgets": list(BUDGETS),
                "random_seeds": RANDOM_SEEDS,
                "audit": "extended",
                "funnel": flow,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (OUTPUT / "rows.json").write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    (OUTPUT / "summary.json").write_text(
        json.dumps({"summary": summary, "decisions": decisions}, indent=1, sort_keys=True) + "\n"
    )
    (OUTPUT / "EVALUATION.md").write_text(report_markdown(flow, summary, decisions, rows))
    print(f"{len(rows)} rows for {len(included)} incidents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
