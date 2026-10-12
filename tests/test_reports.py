"""Result schema 1.0, redaction and renderers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from regressleuth import Incident, investigate
from regressleuth.bench import build_suite, run_one
from regressleuth.cli import exit_code
from regressleuth.errors import ReplayError
from regressleuth.models import STATUSES
from regressleuth.redact import fingerprint, redact_state
from regressleuth.reporting import render_html, render_json, render_markdown, render_text

SCHEMA = Path(__file__).resolve().parents[1] / "src/regressleuth/schemas/result-1.0.schema.json"
SUITE = {spec.id: spec for spec in build_suite()}


def reports_for_every_status(tmp_path: Path) -> dict[str, Any]:
    out = {
        "verified": run_one(SUITE["pair_model_preprocessing_k5"], "adaptive", 16, 0),
        "inferred": run_one(SUITE["control_incompatible_k5"], "adaptive", 16, 0),
        "unresolved": run_one(SUITE["pair_model_preprocessing_k5"], "adaptive", 3, 0),
        "assumption_violated": run_one(SUITE["control_healed_single_k5"], "adaptive", 16, 0),
        "invalid_baseline": run_one(SUITE["control_no_regression_k5"], "adaptive", 16, 0),
        "inconclusive": run_one(SUITE["control_low_signal_k5"], "adaptive", 16, 0),
    }
    incident = Incident.from_spec(
        {
            "version": "1.0",
            "id": "err",
            "good": {"a": 0},
            "bad": {"a": 1},
            "metric": {"name": "m", "direction": "lower_is_better", "regression_threshold": 1},
            "adapter": {"type": "python", "callable": "m:f"},
        },
        base_dir=tmp_path,
    )

    def failing(*_a: Any, **_k: Any) -> float:
        raise ReplayError("x", kind="connection")

    out["evaluation_error"] = investigate(incident, executor=failing)
    return out


def test_every_status_is_produced_and_matches_the_result_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    checker = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
    reports = reports_for_every_status(tmp_path)
    assert {r.status for r in reports.values()} == set(STATUSES)
    for status, report in reports.items():
        data = json.loads(render_json(report))
        errors = sorted(checker.iter_errors(data), key=str)
        assert not errors, (status, errors[:2])
        assert data["status"] == status and data["schema_version"] == "1.0"
        for render in (render_text, render_markdown, render_html):
            assert render(report) == render(data)


def test_result_contains_required_evidence_fields(tmp_path: Path) -> None:
    data = reports_for_every_status(tmp_path)["verified"].to_dict()
    assert data["diagnosis"] == ["model", "preprocessing"]
    assert data["replays"]["isolation_used"] <= data["replays"]["budget"]
    assert data["search"]["hypothesis_count"] == 15 and data["search"]["search_space"] == 32
    assert {a["id"] for a in data["assumptions"]} >= {"fixed_cohort", "monotone_failure", "cause_size"}
    assert next(a for a in data["assumptions"] if a["id"] == "monotone_failure")["status"] == "checked"
    assert data["runtime_seconds"] >= 0 and data["experiments"][0]["hypotheses_remaining"] == 15
    violated = reports_for_every_status(tmp_path)["assumption_violated"].to_dict()
    assert violated["diagnosis"] is None and violated["suspected_cause"]
    assert next(a for a in violated["assumptions"] if a["id"] == "monotone_failure")["status"] == "violated"


def test_exit_codes_are_stable() -> None:
    assert [exit_code(s) for s in STATUSES] == [0, 2, 2, 2, 5, 2, 4]


def test_redaction_policies() -> None:
    state = {
        "model": "v2",
        "token": "abc",
        "url": "https://u:pw@host/x",
        "key": "sk-abcdefghijk",
        "config": {"password": "p", "lr": 0.1},
        "blob": "x" * 300,
    }
    shown = redact_state(state, "redacted")
    assert shown["model"] == "v2" and shown["token"] == "<redacted>" and shown["url"] == "<redacted>"
    assert shown["key"] == "<redacted>" and shown["config"] == {"password": "<redacted>", "lr": 0.1}
    assert shown["blob"].endswith(">") and len(shown["blob"]) < 80
    assert redact_state(state, "hashed")["model"] == fingerprint("v2")
    assert redact_state(state, "omit") is None


def test_html_report_shows_states_lattice_elimination_and_assumptions(tmp_path: Path) -> None:
    (tmp_path / "c.json").write_text("[]")
    incident = Incident.from_spec(
        {
            "version": "1.0",
            "id": "html",
            "good": {"model": "v1", "api_key": "sk-supersecretvalue1"},
            "bad": {"model": "v2", "api_key": "sk-supersecretvalue2"},
            "metric": {"name": "accuracy", "direction": "higher_is_better", "regression_threshold": 0.1},
            "adapter": {"type": "python", "callable": "m:f"},
            "report": {"values": "redacted"},
        },
        base_dir=tmp_path,
    )
    report = investigate(incident, executor=lambda s, *_a, **_k: 0.5 if s["model"] == "v2" else 1.0)
    page = render_html(report)
    for marker in (
        "Good and bad state",
        "Combinations tested",
        "Hypothesis elimination",
        "Assumptions",
        "Budget use",
        "<svg",
        "v1",
        "v2",
        "prefers-color-scheme",
    ):
        assert marker in page
    assert "supersecretvalue" not in page and "supersecretvalue" not in render_json(report)
    assert "## Changed components" in render_markdown(report)
    assert "candidate causes still compatible" in render_text(report)
