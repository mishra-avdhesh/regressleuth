"""Release regression checks for the product and frozen research profiles."""

from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from regressleuth import Incident, investigate
from regressleuth.reporting import render_html, render_json, render_markdown, render_text

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
pytestmark = pytest.mark.skipif(not (BENCHMARKS / "evaluate.py").is_file(), reason="benchmarks not shipped")
if (BENCHMARKS / "evaluate.py").is_file():
    MODULE_SPEC = importlib.util.spec_from_file_location("evaluate", BENCHMARKS / "evaluate.py")
    assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
    evaluate = importlib.util.module_from_spec(MODULE_SPEC)
    MODULE_SPEC.loader.exec_module(evaluate)
CONTROL_NAMES = ("ctrl_tabular_cancelling_pair", "ctrl_text_lowercase_heals")


def control(name: str, *, product_default: bool, tmp_path: Path) -> Incident:
    path = ROOT / "benchmarks" / "higher_order" / "controls" / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text())
    # Stored replay tables supply outcomes; incident validation only needs a cases file.
    cases = tmp_path / "cases.json"
    cases.write_text("[]", encoding="utf-8")
    raw["cases"] = str(cases)
    if product_default:
        raw["budget"].pop("audit")
    incident = Incident.from_spec(raw, base_dir=path.parent)
    if not product_default:
        incident = replace(incident, replay=replace(incident.replay, interval="normal"))
    return incident


@pytest.mark.parametrize("name", CONTROL_NAMES)
def test_known_nonmonotone_controls_never_verify_with_product_default(name: str, tmp_path: Path) -> None:
    incident = control(name, product_default=True, tmp_path=tmp_path)
    assert incident.search.audit == "extended"
    assert incident.replay.interval == "student_t"
    suite = evaluate.suites()["higher_order"]
    table = evaluate.table_of(suite, incident)
    for strategy in evaluate.STRATEGIES:
        for budget in evaluate.BUDGETS:
            limit = evaluate.full_budget(incident) if budget == "full" else int(budget)
            report = investigate(
                incident, budget=limit, strategy=strategy, executor=evaluate.lookup(incident, table)
            )
            assert report.status != "verified", (name, strategy, budget)
            verification = report.to_dict()["verification"]
            assert verification["audit_mode"] == "extended"
            assert verification["interval_method"] == "student_t"


def test_frozen_profile_remains_explicit_and_reproduces_archived_control(tmp_path: Path) -> None:
    config = json.loads((ROOT / "benchmarks" / "configs" / "frozen_2026_10_08.json").read_text())
    assert config["audit"] == "full" and config["interval"] == "normal"
    assert evaluate.evaluate_suite.__kwdefaults__ == {"interval": "normal", "audits": ("full", "extended")}
    incident = control("ctrl_text_lowercase_heals", product_default=False, tmp_path=tmp_path)
    table = evaluate.table_of(evaluate.suites()["higher_order"], incident)
    report = investigate(incident, budget=6, strategy="adaptive", executor=evaluate.lookup(incident, table))
    assert report.status == "verified"
    assert report.to_dict()["verification"]["audit_mode"] == "full"


def test_legacy_user_file_uses_safe_defaults_but_frozen_evaluator_selects_legacy(tmp_path: Path) -> None:
    path = ROOT / "benchmarks" / "incidents" / "tabular_threshold.json"
    raw = json.loads(path.read_text())
    raw["replay"]["cases"] = "cases.json"
    (tmp_path / "cases.json").write_text("[]", encoding="utf-8")
    manifest = tmp_path / path.name
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    incident = Incident.from_file(manifest)
    assert incident.search.audit == "extended"
    assert incident.replay.interval == "student_t"
    assert incident.report_values == "omit"
    config = json.loads((ROOT / "benchmarks" / "configs" / "frozen_2026_10_08.json").read_text())
    assert config["audit"] == "full" and config["interval"] == "normal"


def test_all_report_formats_expose_effective_verification_profile(tmp_path: Path) -> None:
    incident = control("ctrl_tabular_cancelling_pair", product_default=True, tmp_path=tmp_path)
    table = evaluate.table_of(evaluate.suites()["higher_order"], incident)
    report = investigate(incident, budget=8, executor=evaluate.lookup(incident, table))
    data = json.loads(render_json(report))
    verification = data["verification"]
    assert verification["confidence"] == 0.95
    assert verification["repeats"] == verification["max_repeats"] == 1
    assert verification["interval_applied"] is False
    assert "monotone_failure" in verification["assumption_checks"]
    for rendered in (render_text(report), render_markdown(report), render_html(report)):
        assert "audit extended" in rendered
        assert "interval student_t" in rendered
        assert "confidence 0.95" in rendered
        assert "repeats 1/1" in rendered
