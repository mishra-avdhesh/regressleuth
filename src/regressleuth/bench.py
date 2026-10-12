"""SleuthBench-synthetic: oracle incidents with injected ground-truth causes.

Replays are in-process oracles (no model is run); real-model fixtures live under
``benchmarks/`` and ``examples/``. Noisy incidents add reproducible Gaussian metric
noise keyed by (incident, mask, run index), so every strategy sees identical noise
for identical replays.
"""

from __future__ import annotations

import hashlib
import json
import random
import statistics
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .engine import investigate
from .errors import IncompatibleReplay
from .models import Incident, InvestigationReport
from .strategies import STRATEGIES

COMPONENTS = (
    "model",
    "preprocessing",
    "tokenizer",
    "config",
    "inference_data",
    "calibration",
    "threshold",
    "feature_schema",
)
CATEGORY = {
    "model": "model",
    "calibration": "model",
    "preprocessing": "preprocessing",
    "tokenizer": "preprocessing",
    "config": "config",
    "threshold": "config",
    "inference_data": "data_schema",
    "feature_schema": "data_schema",
}
DEFAULT_BUDGETS: tuple[int | str, ...] = (4, 6, 8, 12, 16, 32, "full")
AUDITS = ("full", "extended")
VALID_KINDS = {"single", "pair"}
# controls for which ANY verified cause is unsafe (the monotone single-cause model is false)
STRICT_CONTROLS = {
    "multi_cause",
    "nonmonotone",
    "masked",
    "no_regression",
    "low_signal",
    "cancel_xor",
    "latent_healed",
    "double_healer",
}


@dataclass(frozen=True)
class BenchIncident:
    """kind: single | pair | multi_cause | nonmonotone | masked | incompatible |
    no_regression | low_signal. Only single and pair incidents are valid for scoring
    accuracy; the rest are controls that must never be verified wrongly."""

    id: str
    kind: str
    components: tuple[str, ...]
    cause: frozenset[str]
    category: str
    noise: float = 0.0
    healer: str | None = None

    @property
    def valid(self) -> bool:
        return self.kind in VALID_KINDS

    @property
    def noisy(self) -> bool:
        return self.noise > 0


def build_suite() -> list[BenchIncident]:
    suite: list[BenchIncident] = []
    for k in (5, 6, 8):
        names = COMPONENTS[:k]
        for target in ("model", "preprocessing", "config", "inference_data", "tokenizer"):
            if target in names:
                suite.append(
                    BenchIncident(
                        f"single_{CATEGORY[target]}_{target}_k{k}",
                        "single",
                        names,
                        frozenset((target,)),
                        CATEGORY[target],
                    )
                )
    pairs = [
        (5, ("model", "preprocessing")),
        (5, ("model", "config")),
        (5, ("tokenizer", "inference_data")),
        (6, ("model", "tokenizer")),
        (6, ("preprocessing", "inference_data")),
        (6, ("config", "calibration")),
        (8, ("model", "preprocessing")),
        (8, ("threshold", "feature_schema")),
    ]
    for k, pair in pairs:
        suite.append(
            BenchIncident(
                f"pair_{pair[0]}_{pair[1]}_k{k}",
                "pair",
                COMPONENTS[:k],
                frozenset(pair),
                "interaction",
            )
        )
    noisy = [
        (6, ("model",), 0.02),
        (6, ("preprocessing",), 0.03),
        (8, ("config",), 0.03),
        (8, ("inference_data",), 0.04),
        (6, ("model", "preprocessing"), 0.02),
        (6, ("tokenizer", "config"), 0.03),
        (8, ("model", "config"), 0.04),
        (8, ("preprocessing", "inference_data"), 0.03),
    ]
    for k, cause, sigma in noisy:
        kind = "pair" if len(cause) == 2 else "single"
        suite.append(
            BenchIncident(
                f"noisy_{kind}_{'_'.join(cause)}_k{k}",
                kind,
                COMPONENTS[:k],
                frozenset(cause),
                "noisy",
                noise=sigma,
            )
        )
    names5, names6 = COMPONENTS[:5], COMPONENTS[:6]
    controls = [
        BenchIncident(
            "control_three_way_k6",
            "multi_cause",
            names6,
            frozenset(("model", "preprocessing", "config")),
            "control",
        ),
        BenchIncident(
            "control_nonmonotone_k5", "nonmonotone", names5, frozenset(("model", "preprocessing")), "control"
        ),
        BenchIncident(
            "control_healed_single_k5",
            "masked",
            names5,
            frozenset(("config",)),
            "control",
            healer="tokenizer",
        ),
        BenchIncident(
            "control_healed_pair_k6",
            "masked",
            names6,
            frozenset(("model", "preprocessing")),
            "control",
            healer="calibration",
        ),
        BenchIncident("control_incompatible_k5", "incompatible", names5, frozenset(("config",)), "control"),
        BenchIncident(
            "control_incompatible_pair_k5",
            "incompatible",
            names5,
            frozenset(("tokenizer", "inference_data")),
            "control",
        ),
        BenchIncident("control_no_regression_k5", "no_regression", names5, frozenset(("model",)), "control"),
        BenchIncident(
            "control_low_signal_k5", "low_signal", names5, frozenset(("model",)), "control", noise=0.08
        ),
        # Part D adversarial controls (added after the method freeze; new trace keys only)
        BenchIncident(
            "control_cancel_xor_k5",
            "cancel_xor",
            names5,
            frozenset(("config",)),
            "control",
            healer="model|preprocessing",
        ),
        BenchIncident(
            "control_latent_healed_pair_k6",
            "latent_healed",
            names6,
            frozenset(("config",)),
            "control",
            healer="model|preprocessing|tokenizer",
        ),
        BenchIncident(
            "control_double_healer_k6",
            "double_healer",
            names6,
            frozenset(("model",)),
            "control",
            healer="config|tokenizer|calibration",
        ),
    ]
    return suite + controls


def _noise(spec: BenchIncident, mask: frozenset[str], index: int) -> float:
    if not spec.noisy:
        return 0.0
    digest = hashlib.sha256(f"{spec.id}|{sorted(mask)}|{index}".encode()).hexdigest()
    return random.Random(int(digest[:12], 16)).gauss(0.0, spec.noise)


def _oracle(spec: BenchIncident) -> Callable[..., float]:
    bad = {name: f"{name}:v1" for name in spec.components}
    everything = frozenset(spec.components)
    cause = spec.cause

    def fails(mask: frozenset[str]) -> bool:
        helpers = spec.healer.split("|") if spec.healer else []
        if spec.kind == "cancel_xor":  # a and b each break it, together they cancel; cause also fails
            a, b = helpers
            return ((a in mask) != (b in mask)) or cause <= mask
        if spec.kind == "latent_healed":  # pair a+b fails unless h is bad too; cause fails anyway
            a, b, h = helpers
            return cause <= mask or ({a, b} <= mask and h not in mask)
        if spec.kind == "double_healer":  # cause healed only when h1 and h2 are bad and h3 is not
            h1, h2, h3 = helpers
            return cause <= mask and not (h1 in mask and h2 in mask and h3 not in mask)
        if spec.kind == "nonmonotone":
            a, b = sorted(cause)
            return (a in mask and b not in mask) or mask == everything
        if spec.kind == "masked":
            return cause <= mask and (spec.healer not in mask or mask == everything)
        return cause <= mask

    def evaluate(state: dict[str, Any], _cases: Path, _metric: str, seed: int = 0) -> float:
        mask = frozenset(name for name in spec.components if state[name] == bad[name])
        if spec.kind == "no_regression":
            return 1.0
        if spec.kind == "incompatible":
            first, second = sorted(("model", "preprocessing"))
            if (first in mask) != (second in mask) and mask != everything:
                raise IncompatibleReplay("hybrid cannot be composed")
        effect = 0.12 if spec.kind == "low_signal" else 0.3
        return (1.0 - effect if fails(mask) else 1.0) + _noise(spec, mask, seed)

    return evaluate


def _incident(spec: BenchIncident, directory: Path) -> Incident:
    (directory / "cases.jsonl").write_text('{"case_id": 0, "label": 1}\n', encoding="utf-8")
    replay: dict[str, Any] = {
        "command": ["unused-with-injected-executor"],
        "cases": "cases.jsonl",
        "metric": "accuracy",
        "direction": "higher",
        "regression_threshold": 0.1,
        "timeout_seconds": 1,
    }
    if spec.noisy:
        replay.update({"repeats": 3, "max_repeats": 12, "confidence": 0.95})
    incident = Incident.from_mapping(
        {
            "id": spec.id,
            "good": {name: f"{name}:v0" for name in spec.components},
            "bad": {name: f"{name}:v1" for name in spec.components},
            "replay": replay,
        },
        base_dir=directory,
    )
    # Explicit historical profile for the frozen synthetic behavioral trace.
    return replace(
        incident,
        replay=replace(incident.replay, interval="normal"),
        search=replace(incident.search, audit="full"),
    )


def run_one(
    spec: BenchIncident,
    strategy: str,
    budget: int,
    seed: int,
    audit: int | str = "full",
) -> InvestigationReport:
    with tempfile.TemporaryDirectory() as directory:
        incident = _incident(spec, Path(directory))
        return investigate(
            incident,
            budget=budget,
            strategy=strategy,
            executor=_oracle(spec),
            seed=seed,
            audit=audit,
        )


def _score(spec: BenchIncident, report: InvestigationReport) -> dict[str, float]:
    diagnosis = frozenset(report.diagnosis) if report.diagnosis else None
    verified = report.status == "verified"
    return {
        "exact": float(verified and diagnosis == spec.cause),
        "exact_any": float(diagnosis == spec.cause),
        "wrong_verified": float(verified and (diagnosis != spec.cause or spec.kind in STRICT_CONTROLS)),
        "false_attribution": float(diagnosis is not None and not diagnosis <= spec.cause),
        "unresolved": float(not verified),
        "violated": float(report.status == "assumption_violated"),
        "isolation_cost": float(report.isolation_replays),
        "total_cost": float(report.experiments_used),
        "runs": float(report.total_runs),
        "seconds": sum(e.duration_seconds for e in report.experiments),
    }


def _bootstrap(values: list[float], rng: random.Random, rounds: int = 1000) -> tuple[float, float]:
    if len(values) < 2:
        return (values[0], values[0]) if values else (0.0, 0.0)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(rounds))
    return means[int(0.025 * rounds)], means[int(0.975 * rounds) - 1]


def _summarize(
    strategy: str,
    budget: int | str,
    subset: str,
    scores: list[dict[str, float]],
    pair_exact: list[float],
    control_unsafe: list[float],
    rng: random.Random,
) -> dict[str, Any]:
    low, high = _bootstrap([s["exact"] for s in scores], rng)

    def mean(key: str) -> float:
        return statistics.fmean(s[key] for s in scores)

    return {
        "strategy": strategy,
        "budget": budget,
        "subset": subset,
        "valid_incidents": len(scores),
        "exact_accuracy": mean("exact"),
        "exact_accuracy_ci95": [low, high],
        "exact_any_accuracy": mean("exact_any"),
        "pair_accuracy": statistics.fmean(pair_exact) if pair_exact else None,
        "wrong_verified_rate": mean("wrong_verified"),
        "false_attribution_rate": mean("false_attribution"),
        "unresolved_rate": mean("unresolved"),
        "mean_isolation_replays": mean("isolation_cost"),
        "mean_total_replays": mean("total_cost"),
        "mean_runs": mean("runs"),
        "control_unsafe_verified_rate": statistics.fmean(control_unsafe),
    }


def run_benchmark(
    budgets: tuple[int | str, ...] = DEFAULT_BUDGETS,
    strategies: tuple[str, ...] = STRATEGIES,
    seeds: int = 10,
    audits: tuple[str, ...] = AUDITS,
) -> dict[str, Any]:
    suite = build_suite()
    rows: list[dict[str, Any]] = []
    per_incident: list[dict[str, Any]] = []
    rng = random.Random(20261008)
    for audit in audits:
        for strategy in strategies:
            n_seeds = seeds if strategy == "random" else 1
            for budget in budgets:
                names = ("all", "noisy", "deterministic")
                groups: dict[str, list[dict[str, float]]] = {name: [] for name in names}
                pairs: dict[str, list[float]] = {name: [] for name in names}
                unsafe: list[float] = []
                for spec in suite:
                    limit = 2 ** len(spec.components) if budget == "full" else int(budget)
                    runs = [
                        _score(spec, run_one(spec, strategy, limit, seed, audit=audit))
                        for seed in range(n_seeds)
                    ]
                    mean = {key: statistics.fmean(run[key] for run in runs) for key in runs[0]}
                    per_incident.append(
                        {
                            "strategy": strategy,
                            "budget": budget,
                            "audit": audit,
                            "incident": spec.id,
                            "kind": spec.kind,
                            "noisy": spec.noisy,
                            **mean,
                        }
                    )
                    if spec.valid:
                        for name in ("all", "noisy" if spec.noisy else "deterministic"):
                            groups[name].append(mean)
                            if spec.kind == "pair":
                                pairs[name].append(mean["exact"])
                    else:
                        unsafe.append(mean["wrong_verified"])
                for name in names:
                    row = _summarize(strategy, budget, name, groups[name], pairs[name], unsafe, rng)
                    row["audit"] = audit
                    rows.append(row)
    return {
        "schema_version": 3,
        "suite": [
            {
                "id": s.id,
                "kind": s.kind,
                "components": list(s.components),
                "cause": sorted(s.cause),
                "category": s.category,
                "noise": s.noise,
            }
            for s in suite
        ],
        "budgets": list(budgets),
        "audits": list(audits),
        "random_seeds": seeds,
        "summary": rows,
        "per_incident": per_incident,
    }


def render_markdown(result: dict[str, Any]) -> str:
    kinds = [s["kind"] for s in result["suite"]]
    valid = [s for s in result["suite"] if s["kind"] in VALID_KINDS]
    noisy = [s for s in valid if s["noise"] > 0]
    lines = [
        "# SleuthBench-synthetic results",
        "",
        (
            f"Valid incidents: {len(valid)} ({kinds.count('single')} single-cause, "
            f"{kinds.count('pair')} pair-interaction; {len(noisy)} with metric noise). "
            f"Controls: {len(result['suite']) - len(valid)}. "
            f"Random strategy averaged over {result['random_seeds']} seeds. "
            "Budgets count endpoint, search and verification replays; the monotonicity audit is "
            "extra and appears in total replays. CI is a 95% incident-level bootstrap."
        ),
        "",
    ]
    for subset, title in (("all", "All valid incidents"), ("noisy", "Noisy-metric incidents only")):
        lines += [
            f"## {title}",
            "",
            (
                "| strategy | budget | exact acc. | 95% CI | pair acc. | wrong verified | unresolved "
                "| isolation replays | total replays | runs |"
            ),
            "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in result["summary"]:
            if row["subset"] != subset or row.get("audit", "full") != "full":
                continue
            low, high = row["exact_accuracy_ci95"]
            pair = "n/a" if row["pair_accuracy"] is None else f"{row['pair_accuracy']:.3f}"
            lines.append(
                f"| {row['strategy']} | {row['budget']} | {row['exact_accuracy']:.3f} | "
                f"[{low:.2f}, {high:.2f}] | {pair} | {row['wrong_verified_rate']:.3f} | "
                f"{row['unresolved_rate']:.3f} | {row['mean_isolation_replays']:.1f} | "
                f"{row['mean_total_replays']:.1f} | {row['mean_runs']:.0f} |"
            )
        lines.append("")
    lines += [
        "## Controls: share of control incidents with a verified cause",
        "",
        "Controls are built so that no cause should be verified (healed, cancelling, masked, "
        "three-way, non-monotone, incompatible, no-regression and below-noise failures).",
        "",
        "| strategy | budget | full audit (frozen default) | extended audit (opt-in) | "
        "valid-incident accuracy, extended |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["summary"]:
        if row["subset"] == "all" and row.get("audit", "full") == "full":
            twin = next(
                (
                    r
                    for r in result["summary"]
                    if r["subset"] == "all"
                    and r.get("audit") == "extended"
                    and r["strategy"] == row["strategy"]
                    and r["budget"] == row["budget"]
                ),
                None,
            )
            extended = "-" if twin is None else f"{twin['control_unsafe_verified_rate']:.3f}"
            accuracy = "-" if twin is None else f"{twin['exact_accuracy']:.3f}"
            lines.append(
                f"| {row['strategy']} | {row['budget']} | {row['control_unsafe_verified_rate']:.3f} | "
                f"{extended} | {accuracy} |"
            )
    return "\n".join(lines) + "\n"


def write_results(directory: Path, result: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "sleuthbench_synthetic.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    (directory / "sleuthbench_synthetic.md").write_text(render_markdown(result), encoding="utf-8")
