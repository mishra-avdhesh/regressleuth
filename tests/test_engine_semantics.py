"""Engine semantics: budgets, cause sizes, audits, noise, determinism and fairness."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from pathlib import Path
from typing import Any

import pytest

from regressleuth import Incident, investigate
from regressleuth.bench import build_suite, run_one
from regressleuth.engine import _audit_masks, _requirements
from regressleuth.errors import ReplayError
from regressleuth.strategies import STRATEGIES, candidate_causes

ROOT = Path(__file__).resolve().parents[1]
SUITE = {spec.id: spec for spec in build_suite()}


def make(components: list[str], tmp_path: Path, **replay: Any) -> Incident:
    return Incident.from_spec(
        {
            "version": "1.0",
            "id": "t",
            "good": {c: 0 for c in components},
            "bad": {c: 1 for c in components},
            "metric": {"name": "acc", "direction": "higher_is_better", "regression_threshold": 0.1},
            "replay": replay or {"repeats": 1},
            "adapter": {"type": "python", "callable": "m:f"},
        },
        base_dir=tmp_path,
    )


def oracle(fails: Any) -> Any:
    def evaluate(state: dict[str, int], *_args: Any, seed: int = 0) -> float:
        mask = frozenset(k for k, v in state.items() if v == 1)
        return 0.5 if fails(mask) else 1.0

    return evaluate


def test_candidate_space_and_requirements() -> None:
    components = ("a", "b", "c", "d")
    assert len(candidate_causes(components)) == 4 + 6
    assert len(candidate_causes(components, 3)) == 4 + 6 + 4
    assert len(candidate_causes(components, 1)) == 4
    assert _requirements(frozenset("ab")) == [frozenset("ab"), frozenset("a"), frozenset("b")]
    assert len(_requirements(frozenset("abc"))) == 7
    full = _audit_masks(frozenset("a"), components, extended=False)
    extended = _audit_masks(frozenset("a"), components, extended=True)
    assert len(full) == 1 + 3 and set(full) < set(extended)
    assert frozenset("bc") in extended and frozenset("b") in extended


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_isolation_budget_is_never_exceeded_and_audit_is_reported_separately(strategy: str) -> None:
    for spec in SUITE.values():
        for budget in (2, 5, 9):
            report = run_one(spec, strategy, budget, seed=1)
            assert report.isolation_replays <= budget
            assert report.experiments_used == report.isolation_replays + sum(
                e.role == "audit" for e in report.experiments
            )
            masks = [e.changed for e in report.experiments]
            assert len(masks) == len(set(masks))
            counts = [e.hypotheses_remaining for e in report.experiments]
            assert counts == sorted(counts, reverse=True)


def test_triple_cause_needs_opt_in_and_is_never_verified_by_default(tmp_path: Path) -> None:
    incident = make(["a", "b", "c", "d", "e"], tmp_path)
    triple = oracle(lambda m: {"a", "b", "c"} <= m)
    for strategy in STRATEGIES:
        default = investigate(incident, executor=triple, strategy=strategy, budget=64)
        assert default.status != "verified"
        opted = investigate(incident, executor=triple, strategy=strategy, budget=64, max_cause_size=3)
        if strategy != "one_factor":
            assert opted.status == "verified" and opted.root_cause == ("a", "b", "c"), strategy
    assert investigate(incident, executor=triple, budget=64).status == "assumption_violated"
    single = investigate(incident, executor=oracle(lambda m: "d" in m), budget=64, max_cause_size=1)
    assert single.root_cause == ("d",)
    assert single.search_meta["hypothesis_count"] == 5


@pytest.mark.parametrize(
    "control",
    [
        "control_cancel_xor_k5",
        "control_latent_healed_pair_k6",
        "control_double_healer_k6",
        "control_healed_single_k5",
        "control_nonmonotone_k5",
        "control_three_way_k6",
    ],
)
def test_extended_audit_never_verifies_a_non_monotone_control(control: str) -> None:
    for strategy in STRATEGIES:
        for budget in (8, 16, 64):
            report = run_one(SUITE[control], strategy, budget, seed=0, audit="extended")
            assert report.status != "verified", (control, strategy, budget)


def test_known_blind_spot_of_the_frozen_full_audit_is_documented() -> None:
    """The frozen default audit only probes near the candidate; this is a documented limitation."""
    report = run_one(SUITE["control_double_healer_k6"], "adaptive", 64, seed=0, audit="full")
    assert report.status == "verified"
    extended = run_one(SUITE["control_double_healer_k6"], "adaptive", 64, seed=0, audit="extended")
    assert extended.status == "assumption_violated" and extended.audit["violations"]


def test_noise_statuses(tmp_path: Path) -> None:
    def wobble(state: dict[str, int], *_args: Any, seed: int = 0) -> float:
        rng = random.Random(seed * 31 + state["a"] * 7 + state["b"])
        return 1.0 - 0.05 * state["a"] + rng.gauss(0, 0.5)

    # The explicitly frozen normal interval makes a spurious FAIL here after only three
    # runs; the product-default Student-t interval keeps the result inconclusive.
    normal = investigate(
        make(["a", "b"], tmp_path, repeats=3, max_repeats=6, interval="normal"),
        executor=wobble,
        budget=8,
    )
    assert normal.status == "inferred"
    student = make(["a", "b"], tmp_path, repeats=3, max_repeats=6)
    assert student.replay.interval == "student_t"
    report = investigate(student, executor=wobble, budget=8)
    assert report.status == "inconclusive"
    assert report.to_dict()["confidence"]["interval"] == "student_t"

    def partial(state: dict[str, int], *_args: Any, seed: int = 0) -> float:
        rng = random.Random(seed * 13 + state["a"] * 3 + state["b"])
        drop = 0.4 if state["a"] and state["b"] else (0.1 if state["b"] else 0.0)
        return 1.0 - drop + rng.gauss(0, 0.05)

    report = investigate(student, executor=partial, budget=8)
    assert report.status in {"inconclusive", "verified", "inferred"}
    assert report.total_runs > report.experiments_used


def test_student_t_quantiles_match_reference_values() -> None:
    from regressleuth.stats import t_quantile, welch_df

    for df, expected in ((1, 12.706), (2, 4.303), (4, 2.776), (10, 2.228), (30, 2.042), (1e6, 1.960)):
        assert t_quantile(0.975, df) == pytest.approx(expected, abs=2e-3)
    assert welch_df(1.0, 5, 1.0, 5) == pytest.approx(8.0)
    assert welch_df(0.0, 1, 0.0, 1) == float("inf")


def test_status_vocabulary_for_baseline_and_runtime_problems(tmp_path: Path) -> None:
    incident = make(["a", "b"], tmp_path)
    assert investigate(incident, executor=oracle(lambda m: False), budget=8).status == "invalid_baseline"

    def broken(state: dict[str, int], *_args: Any, **_k: Any) -> float:
        if state == {"a": 1, "b": 0}:
            raise ReplayError("x", kind="timeout")
        return 0.5 if state["a"] and state["b"] else 1.0

    report = investigate(incident, executor=broken, budget=8, strategy="one_factor")
    assert report.status == "evaluation_error"
    assert report.to_dict()["errors"]["kinds"] == {"timeout": 1}
    with pytest.raises(Exception, match="max_cause_size"):
        investigate(incident, executor=broken, max_cause_size=4)
    with pytest.raises(Exception, match="audit"):
        investigate(incident, executor=broken, audit="sometimes")


def digest(report: Any) -> str:
    return hashlib.sha256(
        json.dumps([[e.changed, e.outcome, e.role, e.runs] for e in report.experiments]).encode()
    ).hexdigest()


def test_reproduction_is_deterministic_per_seed() -> None:
    spec = SUITE["noisy_pair_model_preprocessing_k6"]
    for strategy in STRATEGIES:
        assert digest(run_one(spec, strategy, 16, seed=2)) == digest(run_one(spec, strategy, 16, seed=2))
    random_runs = {digest(run_one(spec, "random", 16, seed=s)) for s in range(4)}
    assert len(random_runs) > 1


def test_every_strategy_observes_identical_values_for_identical_replays(tmp_path: Path) -> None:
    """Fairness: the same (combination, run seed) always yields the same observation."""
    incident = make(["a", "b", "c", "d", "e"], tmp_path, repeats=2, max_repeats=6)
    observed: dict[tuple[Any, ...], set[float]] = {}

    def recorder(strategy: str) -> Any:
        def evaluate(state: dict[str, int], *_args: Any, seed: int = 0) -> float:
            mask = tuple(sorted(k for k, v in state.items() if v))
            rng = random.Random(f"{mask}-{seed}")
            value = (0.6 if {"b", "d"} <= set(mask) else 1.0) + rng.gauss(0, 0.03)
            observed.setdefault((mask, seed), set()).add(value)
            return value

        return evaluate

    reports = {s: investigate(incident, executor=recorder(s), strategy=s, budget=32) for s in STRATEGIES}
    assert all(len(values) == 1 for values in observed.values())
    found = {s for s, r in reports.items() if r.diagnosis == ("b", "d")}
    assert found >= {"adaptive", "ddmin", "exhaustive", "greedy"}


@pytest.mark.skipif(not (ROOT / "benchmarks").exists(), reason="benchmarks not shipped in the sdist")
def test_evaluation_harness_replays_the_stored_table_for_every_strategy() -> None:
    from evaluate import lookup

    incident = Incident.from_spec(
        {
            "version": "1.0",
            "id": "tbl",
            "good": {"a": 0, "b": 0, "c": 0},
            "bad": {"a": 1, "b": 1, "c": 1},
            "metric": {"name": "m", "direction": "higher_is_better", "regression_threshold": 0.1},
            "adapter": {"type": "python", "callable": "m:f"},
        },
        base_dir=ROOT,
    )
    table = {
        "|".join(sorted(m)): [{"status": "ok", "metric": 0.5 if {"a", "c"} <= set(m) else 1.0}]
        for size in range(4)
        for m in itertools.combinations("abc", size)
    }
    table["b"] = [{"status": "incompatible", "metric": None}]
    for strategy in STRATEGIES:
        report = investigate(incident, executor=lookup(incident, table), strategy=strategy, budget=8)
        assert all(e.outcome == "incompatible" for e in report.experiments if e.changed == ("b",))
        assert report.status != "verified" or report.root_cause == ("a", "c")


@pytest.mark.skipif(not (ROOT / "benchmarks").exists(), reason="benchmarks not shipped in the sdist")
def test_frozen_default_behavior_is_unchanged_on_a_sample_of_traces() -> None:
    from freeze_method import trace_digest

    frozen = json.loads((ROOT / "benchmarks/frozen/synthetic_trace.json").read_text())
    for key in list(frozen)[::97]:
        incident_id, strategy, budget, seed = key.split("|")
        report = run_one(SUITE[incident_id], strategy, int(budget), int(seed))
        assert trace_digest(report) == frozen[key], key
