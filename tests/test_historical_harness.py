"""Integrity checks for the separate historical benchmark, without outcome assertions."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parents[1]
HISTORICAL = HERE / "benchmarks" / "historical"
if not HISTORICAL.exists():
    pytest.skip("benchmarks not shipped in the sdist", allow_module_level=True)


def load_historical(filename: str, name: str) -> ModuleType:
    """Load a historical benchmark script without leaving its directory on ``sys.path``,
    where its ``evaluate.py`` would shadow ``benchmarks/evaluate.py`` for other tests."""
    sys.path.insert(0, str(HISTORICAL))
    try:
        spec = importlib.util.spec_from_file_location(name, HISTORICAL / filename)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(HISTORICAL))


historical = load_historical("harness.py", "harness")


def candidate(status: str = "included") -> dict[str, object]:
    return {
        "incident_id": "public-bug-1",
        "title": "Public regression",
        "source_urls": ["https://github.com/example/project/issues/1"],
        "source_type": "github_issue",
        "source_date": "2024-01-01",
        "known_good_version": "1.0",
        "known_bad_version": "2.0",
        "changed_components": ["package"],
        "supported_root_cause": ["package"],
        "root_cause_evidence": "Independent issue and replay",
        "fixed_test_cases": "cases.json",
        "failure_metric": "historical_test_pass",
        "threshold": 0.5,
        "reproduction_environment": "Python 3.11",
        "hybrid_replay_feasibility": "full",
        "status": status,
        "exclusion_reasons": [],
    }


def fixture_root(tmp_path: Path, *, included: bool = True) -> Path:
    root = tmp_path / "historical"
    root.mkdir()
    for name in (
        "SELECTION_PROTOCOL.md",
        "ADDENDUM_2026-10-10.md",
        "SEARCH_LOG.md",
        "harness.py",
        "evaluate.py",
        "setup_envs.py",
        "reproduce.py",
        "ENVIRONMENTS.lock.json",
    ):
        (root / name).write_text("frozen\n", encoding="utf-8")
    (root / "FREEZE_MANIFEST.json").write_text(
        json.dumps({"source_tree_sha256": "example"}), encoding="utf-8"
    )
    row = candidate("included" if included else "excluded")
    if not included:
        row["exclusion_reasons"] = ["infeasible_hybrids"]
    (root / "CANDIDATES.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    if included:
        folder = root / "incidents" / "public-bug-1"
        folder.mkdir(parents=True)
        for name in ("incident.yaml", "cases.json", "provenance.json", "runner.py"):
            (folder / name).write_text("fixed\n", encoding="utf-8")
        (folder / "ground_truth.json").write_text(
            json.dumps(
                {
                    "incident_id": "public-bug-1",
                    "established_before_evaluation": True,
                    "accepted_causes": [["package"]],
                    "evidence_urls": ["https://github.com/example/project/issues/1"],
                }
            ),
            encoding="utf-8",
        )
        (folder / "replay_table.json").write_text(
            json.dumps(
                {
                    "table": {
                        "": [{"status": "ok", "metric": 1.0}],
                        "package": [{"status": "ok", "metric": 0.0}],
                    }
                }
            ),
            encoding="utf-8",
        )
    return root


def test_exclusions_need_public_reason() -> None:
    row = candidate("excluded")
    assert "excluded candidate needs coded exclusion_reasons" in historical.candidate_errors(row)
    row["exclusion_reasons"] = ["infeasible_hybrids"]
    assert historical.candidate_errors(row) == []


def test_included_provenance_is_required() -> None:
    row = candidate()
    row["root_cause_evidence"] = None
    assert "included candidate missing root_cause_evidence" in historical.candidate_errors(row)
    row["source_date"] = "2026-10-08"
    assert "source_date must predate the existing benchmark freeze" in historical.candidate_errors(row)


def test_evidence_keeps_ground_truth_separate_and_all_masks(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    historical.validate_evidence(root)
    folder = root / "incidents" / "public-bug-1"
    truth = folder / "ground_truth.json"
    saved = json.loads(truth.read_text(encoding="utf-8"))
    saved["established_before_evaluation"] = False
    truth.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(ValueError, match="ground truth provenance"):
        historical.validate_evidence(root)
    saved["established_before_evaluation"] = True
    truth.write_text(json.dumps(saved), encoding="utf-8")
    (folder / "replay_table.json").write_text(json.dumps({"table": {"": [1]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete replay table"):
        historical.validate_evidence(root)


def test_seal_detects_mutated_cases_and_added_files(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    historical.seal(root)
    historical.verify_seal(root)
    cases = root / "incidents" / "public-bug-1" / "cases.json"
    cases.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="historical seal broken"):
        historical.verify_seal(root)
    cases.write_text("fixed\n", encoding="utf-8")
    (root / "incidents" / "public-bug-1" / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"unexpected\.json"):
        historical.verify_seal(root)


def test_excluded_candidate_remains_logged(tmp_path: Path) -> None:
    root = fixture_root(tmp_path, included=False)
    rows = historical.load_candidates(root / "CANDIDATES.jsonl")
    assert len(rows) == 1
    assert rows[0]["exclusion_reasons"] == ["infeasible_hybrids"]
    historical.validate_evidence(root)


def test_seal_ignores_bytecode_caches(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    historical.seal(root)
    cache = root / "incidents" / "public-bug-1" / "__pycache__"
    cache.mkdir()
    (cache / "runner.cpython-311.pyc").write_bytes(b"\x00")
    historical.verify_seal(root)


def load_evaluator() -> object:
    return load_historical("evaluate.py", "historical_evaluate")


def test_funnel_keeps_excluded_and_disputed_separate() -> None:
    evaluator: object = load_evaluator()
    excluded = candidate("excluded")
    excluded["exclusion_reasons"] = ["no_bad_state", "unfixed_test"]
    disputed = candidate("disputed")
    disputed["incident_id"] = "public-bug-2"
    flow = evaluator.funnel([candidate(), excluded, disputed])  # type: ignore[attr-defined]
    assert flow["logged"] == 3
    assert flow["excluded"] == 1
    assert flow["excluded_by_reason"] == {"no_bad_state": 1, "unfixed_test": 1}
    assert flow["sent_to_reproduction"] == 2
    assert flow["disputed"] == ["public-bug-2"]
    assert flow["included"] == ["public-bug-1"]


def test_evaluation_runs_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    evaluator: object = load_evaluator()
    (tmp_path / "rows.json").write_text("[]\n", encoding="utf-8")
    monkeypatch.setattr(evaluator, "OUTPUT", tmp_path)

    def unreachable() -> None:
        raise AssertionError("an existing evaluation must stop the run before any check")

    monkeypatch.setattr(evaluator, "verify_freeze", unreachable)
    assert evaluator.main() == 3  # type: ignore[attr-defined]
    assert (tmp_path / "rows.json").read_text(encoding="utf-8") == "[]\n"


def test_report_leads_with_funnel_and_wrong_verified() -> None:
    evaluator: object = load_evaluator()
    row = {
        "incident": "public-bug-1",
        "components": 1,
        "search_space": 2,
        "budget": "full",
        "strategy": "adaptive",
        "random_seed": None,
        "status": "verified",
        "diagnosis": ["package"],
        "verified_correct": 0,
        "verified_wrong": 1,
        "inferred_correct": 0,
        "false_attribution": 1,
        "isolation_replays": 2,
        "audit_replays": 0,
        "total_replays": 2,
        "replay_wall_seconds": 0.5,
    }
    summary = evaluator.summarize([row])  # type: ignore[attr-defined]
    flow = evaluator.funnel([candidate()])  # type: ignore[attr-defined]
    text = evaluator.report_markdown([row], summary, flow)  # type: ignore[attr-defined]
    assert text.index("Candidate funnel") < text.index("wrong verified first") < text.index("All metrics")
    assert "| adaptive | full | **1** | 0 |" in text
    assert "Total wrong `verified` diagnoses across all strategy-budget-seed runs: **1**." in text
    assert "Changed components per incident (cause-size strata are reported separately): 1: 1." in text


def test_seal_is_never_replaced(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    historical.seal(root)
    with pytest.raises(ValueError, match="refusing to replace the seal"):
        historical.seal(root)


def test_ledger_component_names_compare_case_insensitively(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    row = json.loads((root / "CANDIDATES.jsonl").read_text(encoding="utf-8"))
    row["changed_components"] = ["Package"]
    (root / "CANDIDATES.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    historical.validate_evidence(root)
    row["changed_components"] = ["other"]
    (root / "CANDIDATES.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete replay table"):
        historical.validate_evidence(root)
