"""Check that the public static snapshots still match the bundled oracle engine."""

from __future__ import annotations

import json
from pathlib import Path

from regressleuth import __version__
from regressleuth.bench import build_suite, run_one

ROOT = Path(__file__).resolve().parents[1] / "space_static"


def test_static_space_snapshots_match_engine() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    suite = {spec.id: spec for spec in build_suite()}
    assert manifest["tool_version"] == __version__
    assert len(manifest["snapshots"]) == 8
    assert (ROOT / "README.md").read_text(encoding="utf-8").startswith("---\ntitle:")

    for item in manifest["snapshots"]:
        report = run_one(suite[item["incident"]], item["strategy"], item["budget"], 0, item["audit"])
        assert item["status"] == report.status
        expected_diagnosis = list(report.diagnosis) if report.diagnosis else None
        assert item["diagnosis"] == expected_diagnosis
        assert item["isolation_replays"] == report.isolation_replays
        assert item["total_replays"] == report.experiments_used
        assert item["audit_replays"] == report.experiments_used - report.isolation_replays
        assert item["interval_applied"] is False
        path = ROOT / item["report"]
        assert path.is_file()
        html = path.read_text(encoding="utf-8")
        assert "Precomputed snapshot" in html
        assert "verified under the configured replay model, assumptions, and audit checks" in html

    controls = [item for item in manifest["snapshots"] if item["incident"] == "control_double_healer_k6"]
    assert all(item["status"] == "assumption_violated" for item in controls if item["audit"] == "extended")
    assert all(item["status"] == "verified" for item in controls if item["audit"] == "full")
