"""Evaluate every strategy on the real-model suites under identical conditions.

    python benchmarks/evaluate.py            # all suites
    python benchmarks/evaluate.py holdout    # one suite

Suites (reported separately, never merged into one headline):
  development  benchmarks/incidents      designed with the method (frozen results exist)
  holdout      benchmarks/holdout        sealed, provenance-backed, evaluated once
  higher_order benchmarks/higher_order   three-way interactions (run with cause size 2 and 3)
Controls of every suite are evaluated for false verification.

Fairness: each strategy replays against the same stored observation table (metric per
combination and run seed, including incompatibilities), with the same budget, the same
driver and the same verification and audit rules. Sealed suites are verified first.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))

from regressleuth import Incident, investigate
from regressleuth.errors import IncompatibleReplay, ReplayError
from regressleuth.strategies import STRATEGIES

BUDGETS: tuple[int | str, ...] = (4, 6, 8, 12, "full")
AUDITS = ("full", "extended")  # historical published comparison; safe-default run is separate
BUDGET_ORDER = {"4": 0, "6": 1, "8": 2, "12": 3, "full": 4}
RANDOM_SEEDS = 10
OUT = ROOT / "results" / "evaluation"


def suites() -> dict[str, dict[str, Any]]:
    return {
        "development": {
            "dir": ROOT,
            "incidents": sorted((ROOT / "incidents").glob("*.json")),
            "controls": sorted((ROOT / "controls").glob("*.json")),
            "tables": ROOT / "results" / "tables",
            "truth": ROOT / "ground_truth.json",
            "sealed": False,
            "cause_sizes": (2,),
        },
        "holdout": {
            "dir": ROOT / "holdout",
            "incidents": sorted((ROOT / "holdout" / "incidents").glob("*.yaml")),
            "controls": sorted((ROOT / "holdout" / "controls").glob("*.yaml")),
            "tables": ROOT / "holdout" / "results" / "tables",
            "truth": ROOT / "holdout" / "ground_truth.json",
            "sealed": True,
            "cause_sizes": (2,),
        },
        "higher_order": {
            "dir": ROOT / "higher_order",
            "incidents": sorted((ROOT / "higher_order" / "incidents").glob("*.yaml")),
            "controls": sorted((ROOT / "higher_order" / "controls").glob("*.yaml")),
            "tables": ROOT / "higher_order" / "results" / "tables",
            "truth": ROOT / "higher_order" / "ground_truth.json",
            "sealed": True,
            "cause_sizes": (2, 3),
        },
    }


def load(path: Path) -> Incident:
    """Load for table replay; a missing cases file (not generated locally) is substituted."""
    try:
        return Incident.from_file(path)
    except Exception:
        raw = json.loads(path.read_text()) if path.suffix == ".json" else None
        if raw is None:
            import yaml

            raw = yaml.safe_load(path.read_text())
        stub = Path(tempfile.mkdtemp()) / "cases.json"
        stub.write_text("[]")
        if "version" in raw:
            raw["cases"] = str(stub)
            return Incident.from_spec(raw, base_dir=path.parent)
        raw["replay"]["cases"] = str(stub)
        return Incident.from_mapping(raw, base_dir=path.parent)


def table_of(suite: dict[str, Any], incident: Incident) -> dict[str, list[dict[str, Any]]]:
    path = suite["tables"] / f"{incident.id}.json"
    if not path.exists():
        sys.path.insert(0, str(ROOT))
        from prove_ground_truth import table_for

        table = table_for(incident, workers=8)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"incident": incident.id, "table": table}))
    return json.loads(path.read_text())["table"]


def lookup(incident: Incident, table: dict[str, list[dict[str, Any]]]) -> Any:
    def evaluator(state: dict[str, Any], _cases: Any, _metric: str, seed: int = 0) -> float:
        key = "|".join(sorted(c for c in incident.changed_components if state[c] == incident.bad[c]))
        entry = table[key][seed]
        status = entry.get("status", "ok" if entry.get("metric") is not None else "incompatible")
        if status == "incompatible":
            raise IncompatibleReplay("incompatible hybrid")
        if status == "error":
            raise ReplayError("replay failed", kind=entry.get("error_kind") or "error")
        return float(entry["metric"])

    return evaluator


def wall(report: Any, table: dict[str, list[dict[str, Any]]]) -> float:
    return sum(
        sum(r.get("seconds", 0.0) for r in table["|".join(e.changed)][: e.runs]) for e in report.experiments
    )


def score(report: Any, cause: frozenset[str] | None) -> dict[str, float]:
    diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
    status = report.status
    row = {
        s: float(status == s)
        for s in (
            "verified",
            "inferred",
            "inconclusive",
            "unresolved",
            "assumption_violated",
            "invalid_baseline",
            "evaluation_error",
        )
    }
    row.update(
        {
            "isolation_replays": float(report.isolation_replays),
            "total_replays": float(report.experiments_used),
            "runner_runs": float(report.total_runs),
        }
    )
    if cause is not None:
        row["verified_right"] = float(status == "verified" and diagnosis == cause)
        row["verified_wrong"] = float(status == "verified" and diagnosis != cause)
        row["inferred_right"] = float(status == "inferred" and diagnosis == cause)
        row["false_attribution"] = float(diagnosis is not None and not diagnosis <= cause)
    else:
        row["verified_wrong"] = float(status == "verified")
    return row


def full_budget(incident: Incident) -> int:
    return 2 ** len(incident.changed_components)


def evaluate_suite(
    name: str,
    suite: dict[str, Any],
    *,
    interval: str = "normal",
    audits: tuple[str, ...] = AUDITS,
) -> list[dict[str, Any]]:
    truth = json.loads(suite["truth"].read_text())
    rows: list[dict[str, Any]] = []
    entries = [(p, False) for p in suite["incidents"]] + [
        (p, True) for p in suite["controls"] if p.name != "expected_status.json"
    ]
    for path, is_control in entries:
        incident = load(path)
        # These stored observations and tables belong to the historical frozen
        # normal-interval profile. Public specification 1.0 now defaults to
        # Student-t; keep the archived comparison explicit and reproducible.
        incident = replace(incident, replay=replace(incident.replay, interval=interval))
        table = table_of(suite, incident)
        cause = None if is_control else frozenset(truth[incident.id])
        for size in suite["cause_sizes"]:
            for audit in audits:
                for strategy in STRATEGIES:
                    for budget in BUDGETS:
                        limit = full_budget(incident) if budget == "full" else int(budget)
                        label = strategy
                        if strategy == "exhaustive" and limit < full_budget(incident):
                            label = "exhaustive_order"
                        seeds = range(RANDOM_SEEDS) if strategy == "random" else range(1)
                        per_seed = []
                        for seed in seeds:
                            report = investigate(
                                incident,
                                budget=limit,
                                strategy=strategy,
                                seed=seed,
                                executor=lookup(incident, table),
                                audit=audit,
                                max_cause_size=size,
                            )
                            result = score(report, cause)
                            result["wall_seconds"] = wall(report, table)
                            result["status"] = report.status
                            per_seed.append(result)
                        numeric = {
                            k: statistics.fmean(r[k] for r in per_seed) for k in per_seed[0] if k != "status"
                        }
                        rows.append(
                            {
                                "suite": name,
                                "incident": incident.id,
                                "control": is_control,
                                "components": len(incident.changed_components),
                                "cause_size": len(cause) if cause else None,
                                "max_cause_size": size,
                                "audit": audit,
                                "strategy": strategy,
                                "label": label,
                                "budget": budget,
                                "limit": limit,
                                "statuses": sorted({r["status"] for r in per_seed}),
                                "seed_values": {
                                    "verified_right": [r.get("verified_right", 0.0) for r in per_seed]
                                },
                                **numeric,
                            }
                        )
        print(f"  {name}: {incident.id} done", flush=True)
    return rows


def bootstrap(values: list[float], seed: int = 20261008, rounds: int = 2000) -> list[float]:
    """Percentile bootstrap over incidents for fractional per-incident outcomes."""
    if len(values) < 2:
        return [values[0], values[0]] if values else [0.0, 0.0]
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(rounds))
    return [means[int(0.025 * rounds)], means[int(0.975 * rounds) - 1]]


def incident_interval(values: list[float]) -> tuple[list[float], str]:
    """Use Wilson for binary outcomes; otherwise resample incident clusters.

    A percentile bootstrap of all-success binary outcomes incorrectly returns
    [1, 1]. Random search first averages ten seeds per incident, so its
    fractional outcomes retain the incident-level bootstrap.
    """
    if not values:
        raise ValueError("an incident interval needs at least one outcome")
    if any(value not in (0.0, 1.0) for value in values):
        return bootstrap(values), "incident_cluster_bootstrap"
    n = len(values)
    proportion = statistics.fmean(values)
    z = statistics.NormalDist().inv_cdf(0.975)
    z2 = z * z
    denominator = 1 + z2 / n
    center = (proportion + z2 / (2 * n)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / n + z2 / (4 * n * n)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)], "wilson"


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key_of(r: dict[str, Any]) -> tuple[Any, ...]:
        return (r["suite"], r["max_cause_size"], r["audit"], r["strategy"], str(r["budget"]))

    keys = sorted(
        {key_of(r) for r in rows},
        key=lambda k: (k[0], k[1], k[2], STRATEGIES.index(k[3]), BUDGET_ORDER[k[4]]),
    )
    out = []
    for key in keys:
        suite, size, audit, strategy, budget = key
        sel = [r for r in rows if key_of(r) == key and not r["control"]]
        controls = [r for r in rows if key_of(r) == key and r["control"]]
        if not sel:
            continue
        labels = sorted({r["label"] for r in sel})

        def mean(key: str, subset: list[dict[str, Any]] = sel) -> float | None:
            values = [r[key] for r in subset if key in r]
            return statistics.fmean(values) if values else None

        by_size: dict[str, float | None] = {}
        for cause_size, label in ((1, "single"), (2, "pair"), (3, "triple")):
            subset = [r for r in sel if r["cause_size"] == cause_size]
            by_size[f"{label}_verified_right"] = mean("verified_right", subset)
            by_size[f"{label}_n"] = len(subset)
        seed_ci = None
        if strategy == "random":
            per_seed = [
                statistics.fmean(r["seed_values"]["verified_right"][s] for r in sel)
                for s in range(RANDOM_SEEDS)
            ]
            mu = statistics.fmean(per_seed)
            half = 2.262 * statistics.stdev(per_seed) / math.sqrt(RANDOM_SEEDS)
            seed_ci = [mu - half, mu + half]
        incident_ci, incident_ci_method = incident_interval([r["verified_right"] for r in sel])
        out.append(
            {
                "suite": suite,
                "max_cause_size": size,
                "audit": audit,
                "strategy": strategy,
                "label": labels[0] if len(labels) == 1 else "exhaustive_order/exhaustive",
                "budget": budget,
                "incidents": len(sel),
                "verified_right": mean("verified_right"),
                "verified_right_ci95_incidents": incident_ci,
                "verified_right_ci95_incidents_method": incident_ci_method,
                "verified_right_ci95_seeds": seed_ci,
                "verified_wrong": mean("verified_wrong"),
                "inferred_unverified": mean("inferred"),
                "inferred_right": mean("inferred_right"),
                "unresolved": mean("unresolved"),
                "inconclusive": mean("inconclusive"),
                "assumption_violated": mean("assumption_violated"),
                "false_attribution": mean("false_attribution"),
                "median_isolation_replays": statistics.median(r["isolation_replays"] for r in sel),
                "mean_isolation_replays": mean("isolation_replays"),
                "mean_total_replays": mean("total_replays"),
                "mean_wall_seconds": mean("wall_seconds"),
                "controls": len(controls),
                "controls_false_verified": mean("verified_wrong", controls) if controls else None,
                **by_size,
            }
        )
    return out


def render(summary: list[dict[str, Any]], rows: list[dict[str, Any]]) -> str:
    def pct(value: float | None) -> str:
        return "-" if value is None else f"{100 * value:.0f}%"

    lines = [
        "# Evaluation: development, holdout and higher-order suites",
        "",
        "Generated by `benchmarks/evaluate.py`. Each suite is reported on its own. Budgets count "
        "endpoint, search and verification replays; audits are extra. `full` allows enumerating every combination "
        "(2^k). `exhaustive_order` is exhaustive enumeration cut off by a smaller budget. "
        f"Random is averaged over {RANDOM_SEEDS} seeds. Rates are over valid incidents; controls "
        "are listed separately.",
        "",
        "The 95% incident interval uses Wilson's score method for binary per-incident success. "
        "For fractional outcomes averaged over random-search seeds, it uses a percentile bootstrap "
        "that resamples incidents. These intervals describe this small, author-constructed set and "
        "do not account for dependencies between incidents. Runner seconds sum stored replay "
        "durations; they are not end-to-end wall time.",
        "",
    ]
    titles = {
        ("development", 2): "Development suite (designed with the method)",
        ("holdout", 2): "Author-constructed sealed validation suite (called holdout)",
        ("higher_order", 2): "Higher-order suite, frozen default (causes of at most 2 components)",
        ("higher_order", 3): "Higher-order suite, opt-in search for causes of up to 3 components",
    }
    for (suite, size), title in titles.items():
        sel = [
            s for s in summary if s["suite"] == suite and s["max_cause_size"] == size and s["audit"] == "full"
        ]
        if not sel:
            continue
        n = sel[0]["incidents"]
        lines += [
            f"## {title} ({n} incidents)",
            "",
            "| strategy | budget | verified right | 95% CI | inferred (not verified) | unresolved "
            "| inconclusive | assumption violated | false attribution | median / mean isolation replays | runner s |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for s in sel:
            ci = s["verified_right_ci95_incidents"]
            lines.append(
                f"| {s['label']} | {s['budget']} | {pct(s['verified_right'])} | "
                f"[{pct(ci[0])}, {pct(ci[1])}] | {pct(s['inferred_unverified'])} | {pct(s['unresolved'])} | "
                f"{pct(s['inconclusive'])} | {pct(s['assumption_violated'])} | {pct(s['false_attribution'])} | "
                f"{s['median_isolation_replays']:.0f} / {s['mean_isolation_replays']:.1f} | "
                f"{s['mean_wall_seconds']:.1f} |"
            )
        lines.append("")
        sizes = [("single", "single_n"), ("pair", "pair_n"), ("triple", "triple_n")]
        present = [(label, key) for label, key in sizes if sel[0][key]]
        lines += [
            f"Verified-right rate by cause size ({', '.join(f'{lab} n={sel[0][key]}' for lab, key in present)}):",
            "",
            "| strategy | budget | " + " | ".join(lab for lab, _ in present) + " |",
            "|---|---|" + "---:|" * len(present),
        ]
        for s in sel:
            lines.append(
                f"| {s['label']} | {s['budget']} | "
                + " | ".join(pct(s[f"{lab}_verified_right"]) for lab, _ in present)
                + " |"
            )
        lines.append("")
    lines += [
        "## Extended audit (opt-in) versus the frozen full audit",
        "",
        "The extended audit was added after the first evaluation showed false verifications on "
        "the designed higher-order controls. It was not tuned on the holdout; holdout numbers "
        "with it are a post-hoc configuration, reported for completeness.",
        "",
        "| suite | cause size | strategy | budget | audit | verified right | false verified (incidents) "
        "| controls false-verified | mean total replays |",
        "|---|---:|---|---|---|---:|---:|---:|---:|",
    ]
    for s in summary:
        if s["strategy"] in {"adaptive", "ddmin"} and s["budget"] in {"12", "full"}:
            lines.append(
                f"| {s['suite']} | {s['max_cause_size']} | {s['label']} | {s['budget']} | {s['audit']} "
                f"| {pct(s['verified_right'])} | {pct(s['verified_wrong'])} "
                f"| {pct(s['controls_false_verified'])} | {s['mean_total_replays']:.1f} |"
            )
    lines.append("")
    controls = [r for r in rows if r["control"]]
    if controls:
        lines += [
            "## Controls: no cause may be verified",
            "",
            "| suite | control | cause size searched | audit | strategies x budgets | statuses seen "
            "| runs with a verified cause |",
            "|---|---|---:|---|---:|---|---:|",
        ]
        for key in sorted({(r["suite"], r["incident"], r["max_cause_size"], r["audit"]) for r in controls}):
            sel = [r for r in controls if (r["suite"], r["incident"], r["max_cause_size"], r["audit"]) == key]
            statuses = sorted({s for r in sel for s in r["statuses"]})
            false = sum(r["verified_wrong"] > 0 for r in sel)
            lines.append(
                f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} | {len(sel)} | {', '.join(statuses)} "
                f"| {false} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main(selected: tuple[str, ...], *, interval: str = "normal", audits: tuple[str, ...] = AUDITS) -> int:
    all_suites = suites()
    for name, suite in all_suites.items():
        if suite["sealed"] and (not selected or name in selected):
            check = subprocess.run(
                [sys.executable, str(ROOT / "seal.py"), "verify", str(suite["dir"])],
                capture_output=True,
                text=True,
            )
            print(check.stdout.strip())
            if check.returncode != 0:
                return 1
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for name, suite in all_suites.items():
        if selected and name not in selected:
            continue
        print(f"evaluating {name}", flush=True)
        rows += evaluate_suite(name, suite, interval=interval, audits=audits)
    previous = OUT / "rows.json"
    if selected and previous.exists():
        rows = [r for r in json.loads(previous.read_text()) if r["suite"] not in selected] + rows
    summary = summarize(rows)
    previous.write_text(json.dumps(rows))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    (OUT / "EVALUATION.md").write_text(render(summary, rows))
    print(f"wrote {OUT / 'EVALUATION.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(tuple(sys.argv[1:])))
