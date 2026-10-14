"""Lockfile-update suite tooling: ledger rules and seal protection."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parents[1]
LOCKDRIFT = HERE / "benchmarks" / "lockdrift"
if not LOCKDRIFT.exists():
    pytest.skip("benchmarks not shipped in the sdist", allow_module_level=True)


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lockdrift_harness", LOCKDRIFT / "harness.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = load_harness()


def candidate(status: str = "candidate", **extra: object) -> dict[str, object]:
    return {
        "incident_id": "lock-1",
        "title": "Bump the deps group with 3 updates",
        "source_urls": ["https://github.com/example/project/pull/1"],
        "source_date": "2026-01-01",
        "project": "example/project",
        "status": status,
        "exclusion_reasons": [],
        **extra,
    }


def test_ledger_codes_and_replay_fields() -> None:
    assert harness.candidate_errors(candidate()) == []
    assert harness.candidate_errors(candidate("excluded", exclusion_reasons=["python_unavailable"])) == []
    assert harness.candidate_errors(candidate("excluded", exclusion_reasons=["download_too_large"]))
    errors = harness.candidate_errors(candidate("disputed"))
    assert any("base_commit" in e for e in errors) and any("ci_selection" in e for e in errors)


def test_addenda_are_sealed_and_a_seal_is_never_replaced(tmp_path: Path) -> None:
    root = tmp_path / "lockdrift"
    root.mkdir()
    for name in harness.TRACKED:
        (root / name).write_text("{}\n" if name.endswith(".json") else "x\n", encoding="utf-8")
    (root / "FREEZE_MANIFEST.json").write_text(
        json.dumps({"tree_sha256": "t", "files": {}}), encoding="utf-8"
    )
    (root / "ADDENDUM_2026-01-01.md").write_text("clarification\n", encoding="utf-8")
    sealed = harness.seal(root)
    assert "ADDENDUM_2026-01-01.md" in sealed["files"]
    (root / "ADDENDUM_2026-01-01.md").write_text("edited\n", encoding="utf-8")
    with pytest.raises(ValueError, match="seal broken"):
        harness.verify_seal(root)
    with pytest.raises(ValueError, match="refusing to replace the seal"):
        harness.seal(root)
