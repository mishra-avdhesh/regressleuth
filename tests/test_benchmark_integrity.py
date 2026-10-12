"""Benchmark integrity: seals, ground-truth proofs, frozen development results, fairness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks"
pytestmark = pytest.mark.skipif(not BENCH.exists(), reason="benchmarks are not shipped in the sdist")


@pytest.mark.parametrize("suite", ["holdout", "higher_order"])
def test_sealed_suites_are_unchanged(suite: str) -> None:
    command = [sys.executable, str(BENCH / "seal.py"), "verify", str(BENCH / suite)]
    if not (BENCH / suite / "data").exists():
        command.append("--definitions-only")  # fresh clone: generated data is not committed
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("suite", ["holdout", "higher_order"])
def test_every_ground_truth_was_proved_by_exhaustive_replay(suite: str) -> None:
    proofs = json.loads((BENCH / suite / "results" / "ground_truth_proofs.json").read_text())
    truth = json.loads((BENCH / suite / "ground_truth.json").read_text())
    assert set(proofs) == set(truth)
    for incident, proof in proofs.items():
        assert proof["proved"] and not proof["violations"], incident
        assert proof["combinations"] == 32


def test_evaluation_reproduces_the_frozen_development_results() -> None:
    rows_path = BENCH / "results" / "evaluation" / "rows.json"
    if not rows_path.exists():
        pytest.skip("run benchmarks/evaluate.py first")
    frozen = json.loads((BENCH / "frozen" / "real_dev_results.json").read_text())
    rows = [
        r
        for r in json.loads(rows_path.read_text())
        if r["suite"] == "development" and not r["control"] and r["audit"] == "full" and r["budget"] != "full"
    ]
    compared = 0
    for row in rows:
        key = f"{row['incident']}|{row['strategy']}|{row['budget']}"
        if key in frozen:
            expected = frozen[key]
            assert [
                row["verified_right"],
                row["isolation_replays"],
                row["total_replays"],
                row["runner_runs"],
            ] == pytest.approx([expected[0], expected[2], expected[3], expected[4]]), key
            compared += 1
    assert compared >= 500


def test_holdout_results_report_no_false_verification_on_valid_incidents() -> None:
    summary_path = BENCH / "results" / "evaluation" / "summary.json"
    if not summary_path.exists():
        pytest.skip("run benchmarks/evaluate.py first")
    for row in json.loads(summary_path.read_text()):
        assert row["verified_wrong"] == 0, row
        if row["audit"] == "extended":
            assert not row["controls_false_verified"], row
