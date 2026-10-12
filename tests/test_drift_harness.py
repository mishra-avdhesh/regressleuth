"""Dependency-drift suite tooling: ground truth, ledger rules and the one-time evaluator."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parents[1]
DRIFT = HERE / "benchmarks" / "drift"
if not DRIFT.exists():
    pytest.skip("benchmarks not shipped in the sdist", allow_module_level=True)


def load(filename: str, name: str) -> ModuleType:
    sys.path.insert(0, str(DRIFT))
    sys.path.insert(0, str(HERE / "benchmarks"))
    try:
        spec = importlib.util.spec_from_file_location(name, DRIFT / filename)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for entry in (str(DRIFT), str(HERE / "benchmarks")):
            if entry in sys.path:
                sys.path.remove(entry)


# evaluate.py imports ``harness`` by name, as does the historical suite; register the drift
# harness under that name only while the evaluator loads, then restore the previous entry
_previous = sys.modules.get("harness")
_path = list(sys.path)  # the scripts extend sys.path; restore it so other suites' modules resolve
harness = load("harness.py", "harness")
drift = load("drift.py", "drift_tool")
evaluator = load("evaluate.py", "drift_evaluate")
sys.path[:] = _path
if _previous is not None:
    sys.modules["harness"] = _previous
else:
    del sys.modules["harness"]


def table(outcomes: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out = {}
    for key, value in outcomes.items():
        if value == "incompatible":
            out[key] = [{"status": "incompatible", "metric": None, "error_kind": None, "seconds": 0.1}]
        else:
            out[key] = [{"status": "ok", "metric": value, "error_kind": None, "seconds": 0.1}]
    return out


def test_strict_and_coupled_minimal_failing_sets() -> None:
    components = ("a", "b", "c")
    strict = table({"": 1.0, "a": 0.0, "b": 1.0, "c": 1.0, "a|b": 0.0, "a|c": 0.0, "b|c": 1.0, "a|b|c": 0.0})
    assert drift.minimal_failing(components, strict) == ([["a"]], [])
    # b alone cannot be installed with old c: the failing pair b+c is coupled-minimal
    coupled = table(
        {
            "": 1.0,
            "a": 1.0,
            "b": "incompatible",
            "c": 1.0,
            "a|b": "incompatible",
            "a|c": 1.0,
            "b|c": 0.0,
            "a|b|c": 0.0,
        }
    )
    assert drift.minimal_failing(components, coupled) == ([], [["b", "c"]])


def candidate(status: str = "candidate", **extra: Any) -> dict[str, Any]:
    return {
        "incident_id": "drift-1",
        "title": "Tests fail with new release",
        "source_urls": ["https://github.com/example/project/issues/1"],
        "source_date": "2024-01-01",
        "project": "example/project",
        "status": status,
        "exclusion_reasons": [],
        **extra,
    }


def test_ledger_rules() -> None:
    assert harness.candidate_errors(candidate()) == []
    assert "excluded candidate needs coded exclusion_reasons" in harness.candidate_errors(
        candidate("excluded")
    )
    assert harness.candidate_errors(candidate("excluded", exclusion_reasons=["build_infeasible"])) == []
    assert harness.candidate_errors(candidate("excluded", exclusion_reasons=["made_up"]))
    assert any(
        "required for a replayed candidate" in e for e in harness.candidate_errors(candidate("included"))
    )


def test_evaluator_runs_every_strategy_on_a_stored_table(tmp_path: Path) -> None:
    from regressleuth import Incident

    incident = Incident.from_spec(
        {
            "version": "1.0",
            "id": "drift-1",
            "good": {"a": "1.0", "b": "1.0", "c": "absent"},
            "bad": {"a": "2.0", "b": "2.0", "c": "0.3"},
            "metric": {
                "name": "drift_tests_pass",
                "direction": "higher_is_better",
                "regression_threshold": 0.5,
            },
            "adapter": {"type": "python", "callable": "stored:table"},
        },
        base_dir=tmp_path,
    )
    stored = table(
        {"": 1.0, "a": 1.0, "b": 1.0, "c": 1.0, "a|b": 0.0, "a|c": 1.0, "b|c": "incompatible", "a|b|c": 0.0}
    )
    truth = {"accepted_causes": [["a", "b"]], "coupled_minimal": []}
    rows = evaluator.evaluate_one(incident, stored, truth)
    assert {r["strategy"] for r in rows} == {
        "adaptive",
        "ddmin",
        "exhaustive",
        "greedy",
        "one_factor",
        "random",
    }
    full = {r["strategy"]: r for r in rows if r["budget"] == "full" and r["random_seed"] in (None, 0)}
    assert full["adaptive"]["diagnosis"] == ["a", "b"] and full["adaptive"]["verified_wrong"] == 0
    decision = evaluator.paired(rows, "full")
    assert decision["adaptive_wins"] + decision["ddmin_wins"] + decision["ties"] == 1
    assert not decision["claim_supported"]


def test_drift_seal_is_never_replaced(tmp_path: Path) -> None:
    root = tmp_path / "drift"
    root.mkdir()
    for name in harness.TRACKED:
        (root / name).write_text("{}\n" if name.endswith(".json") else "x\n", encoding="utf-8")
    (root / "FREEZE_MANIFEST.json").write_text(
        json.dumps({"tree_sha256": "t", "files": {}}), encoding="utf-8"
    )
    harness.seal(root)
    harness.verify_seal(root)
    (root / "CANDIDATES.jsonl").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="seal broken"):
        harness.verify_seal(root)
    with pytest.raises(ValueError, match="refusing to replace the seal"):
        harness.seal(root)


def test_generated_ruff_cache_is_not_sealed(tmp_path: Path) -> None:
    root = tmp_path / "drift"
    root.mkdir()
    for name in harness.TRACKED:
        (root / name).write_text("{}\n" if name.endswith(".json") else "x\n", encoding="utf-8")
    (root / "FREEZE_MANIFEST.json").write_text(
        json.dumps({"tree_sha256": "t", "files": {}}), encoding="utf-8"
    )
    cache = root / "incidents" / ".ruff_cache" / "version" / "entry"
    cache.parent.mkdir(parents=True)
    cache.write_text("generated", encoding="utf-8")
    harness.seal(root)
    cache.write_text("changed", encoding="utf-8")
    harness.verify_seal(root)


def test_evaluation_refuses_partial_existing_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(evaluator, "OUTPUT", tmp_path)
    (tmp_path / "RUN.json").write_text("partial\n", encoding="utf-8")
    assert evaluator.main() == 3
