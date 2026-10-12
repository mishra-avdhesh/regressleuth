"""Incident Specification 1.0: validation, messages, loading and JSON Schema agreement."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from regressleuth import Incident
from regressleuth.errors import InvalidIncident
from regressleuth.spec import load_document, validate

SCHEMA = Path(__file__).resolve().parents[1] / "src/regressleuth/schemas/incident-1.0.schema.json"


def valid() -> dict[str, Any]:
    return {
        "version": "1.0",
        "id": "inc-1",
        "good": {"model": "v1", "prep": {"lower": True}},
        "bad": {"model": "v2", "prep": {"lower": False}},
        "metric": {"name": "accuracy", "direction": "higher_is_better", "regression_threshold": 0.02},
        "adapter": {"type": "command", "command": ["{python}", "run.py", "{state}", "{result}"]},
    }


def problems_for(mutate: Any) -> list[str]:
    doc = valid()
    mutate(doc)
    return validate(doc)


def test_valid_document_has_no_problems_and_builds_with_defaults(tmp_path: Path) -> None:
    assert validate(valid()) == []
    incident = Incident.from_spec(valid(), base_dir=tmp_path)
    assert incident.changed_components == ("model", "prep")
    assert incident.search.budget == 16 and incident.search.audit == "extended"
    assert incident.search.strategy == "adaptive" and incident.search.max_cause_size == 2
    assert incident.report_values == "omit" and incident.spec_version == "1.0"
    assert incident.replay.interval == "student_t"
    assert incident.replay.direction == "higher" and incident.replay.cases is None


CASES = [
    (lambda d: d.update(extra=1), "extra: unknown key"),
    (lambda d: d.update(version="2.0"), "version: must be the string"),
    (lambda d: d.update(version=1.0), "version: must be the string"),
    (lambda d: d.update(id="bad id!"), "id: 1-128 characters"),
    (lambda d: d.pop("metric"), "metric: required"),
    (lambda d: d["bad"].update(new=1), "good.new: missing"),
    (lambda d: d.update(good={"9bad": 1}, bad={"9bad": 2}), "component names must match"),
    (lambda d: d.update(bad=copy.deepcopy(d["good"])), "no component differs"),
    (
        lambda d: d.update(good={f"c{i}": 0 for i in range(13)}, bad={f"c{i}": 1 for i in range(13)}),
        "at most 12 are supported",
    ),
    (lambda d: d["good"].update(model=float("nan")), "without NaN"),
    (lambda d: d["metric"].update(direction="higher"), "metric.direction: must be one of"),
    (lambda d: d["metric"].update(regression_threshold=0), "metric.regression_threshold"),
    (lambda d: d["metric"].update(unit="%"), "metric.unit: unknown key"),
    (lambda d: d.update(replay={"repeats": 0}), "replay.repeats: integer from 1 to 1000"),
    (lambda d: d.update(replay={"repeats": 4, "max_repeats": 2}), "max_repeats: must be at least"),
    (lambda d: d.update(replay={"confidence": 1.0}), "replay.confidence"),
    (lambda d: d.update(replay={"seeds": 3}), "replay.seeds: unknown key"),
    (lambda d: d.update(search={"strategy": "magic"}), "search.strategy"),
    (lambda d: d.update(search={"max_cause_size": 4}), "search.max_cause_size"),
    (lambda d: d.update(search={"seed": -1}), "search.seed"),
    (lambda d: d.update(budget={"max_replays": 1}), "budget.max_replays"),
    (lambda d: d.update(budget={"audit": "partial"}), "budget.audit"),
    (lambda d: d.update(adapter={"type": "ssh"}), "adapter.type: one of"),
    (lambda d: d.update(adapter={"type": "command"}), "adapter.command: required"),
    (lambda d: d["adapter"].update(command="python run.py"), "adapter.command: non-empty list"),
    (lambda d: d["adapter"].update(env={"A": 1}), "adapter.env"),
    (lambda d: d["adapter"].update(timeout_seconds=0), "adapter.timeout_seconds"),
    (
        lambda d: d["adapter"].update(interpreters={"component": "model", "map": {"v1": "py"}}),
        "no entry for bad.model",
    ),
    (
        lambda d: d["adapter"].update(interpreters={"component": "gpu", "map": {"a": "b"}}),
        "'gpu' is not a component",
    ),
    (lambda d: d.update(adapter={"type": "python", "callable": "nocolon"}), "adapter.callable"),
    (lambda d: d.update(adapter={"type": "http", "base_url": "ftp://x"}), "adapter.base_url"),
    (lambda d: d.update(adapter={"type": "http", "base_url": "http://x"}), "cases: required"),
    (
        lambda d: d.update(
            adapter={"type": "http", "base_url": "http://x", "mode": "evaluate", "components_via": "query"}
        ),
        "adapter.components_via",
    ),
    (lambda d: d.update(adapter={"type": "docker", "command": ["run"]}), "exactly one of image or images"),
    (lambda d: d.update(report={"values": "plain"}), "report.values"),
    (lambda d: d.update(metadata=[]), "metadata: must be a mapping"),
    (lambda d: d.update(cases=""), "cases: must be a non-empty relative path"),
]


@pytest.mark.parametrize(("mutate", "message"), CASES)
def test_each_rule_reports_a_located_message(mutate: Any, message: str) -> None:
    problems = problems_for(mutate)
    assert any(message in problem for problem in problems), problems


def test_all_problems_are_reported_at_once() -> None:
    doc = valid()
    doc.update(id="x y", extra=True)
    doc["metric"]["direction"] = "up"
    assert len(validate(doc)) >= 3
    assert validate("not a mapping") == ["(document): must be a mapping"]


def test_from_spec_raises_with_problem_list(tmp_path: Path) -> None:
    doc = valid()
    doc["metric"]["direction"] = "up"
    with pytest.raises(InvalidIncident) as caught:
        Incident.from_spec(doc, base_dir=tmp_path)
    assert caught.value.problems and "metric.direction" in caught.value.problems[0]


def test_missing_cases_file_is_reported(tmp_path: Path) -> None:
    doc = valid()
    doc["cases"] = "missing.json"
    with pytest.raises(InvalidIncident, match="cases: file not found"):
        Incident.from_spec(doc, base_dir=tmp_path)


def test_yaml_duplicate_keys_and_syntax_errors_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.yaml"
    path.write_text("version: '1.0'\nid: a\nid: b\n", encoding="utf-8")
    with pytest.raises(InvalidIncident, match=r"duplicate key 'id'.*line 3"):
        load_document(path)
    path.write_text("version: [unclosed\n", encoding="utf-8")
    with pytest.raises(InvalidIncident, match="line"):
        load_document(path)
    json_path = tmp_path / "dup.json"
    json_path.write_text('{"id": 1, "id": 2}', encoding="utf-8")
    with pytest.raises(InvalidIncident, match="duplicate key"):
        load_document(json_path)
    with pytest.raises(InvalidIncident, match="cannot read"):
        load_document(tmp_path / "absent.yaml")


def test_yaml_file_round_trip_and_legacy_json(tmp_path: Path) -> None:
    import yaml

    (tmp_path / "cases.json").write_text("[]")
    doc = valid() | {
        "cases": "cases.json",
        "search": {"max_cause_size": 3, "seed": 4},
        "budget": {"max_replays": 9, "audit": "extended"},
        "replay": {"repeats": 2},
    }
    (tmp_path / "incident.yaml").write_text(yaml.safe_dump(doc))
    incident = Incident.from_file(tmp_path / "incident.yaml")
    assert incident.search.max_cause_size == 3 and incident.search.seed == 4
    assert incident.search.budget == 9 and incident.search.audit == "extended"
    assert incident.replay.repeats == 2 and incident.replay.max_repeats == 2
    legacy = {
        "id": "old",
        "good": {"a": 1},
        "bad": {"a": 2},
        "replay": {
            "command": ["x"],
            "cases": "cases.json",
            "metric": "m",
            "direction": "lower",
            "regression_threshold": 1,
            "timeout_seconds": 3,
        },
    }
    (tmp_path / "old.json").write_text(json.dumps(legacy))
    assert Incident.from_file(tmp_path / "old.json").spec_version == "legacy"


def structural_corpus() -> list[tuple[dict[str, Any], bool]]:
    corpus = [(valid(), True)]
    for mutate, _ in CASES:
        doc = valid()
        try:
            mutate(doc)
        except Exception:
            continue
        corpus.append((doc, False))
    return corpus


SEMANTIC_ONLY = {
    "good.new: missing",
    "no component differs",
    "at most 12 are supported",
    "without NaN",
    "max_repeats: must be at least",
    "no entry for bad.model",
    "is not a component",
    "cases: required",
}


def test_json_schema_agrees_with_the_validator_on_structural_rules() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    checker = jsonschema.Draft202012Validator(schema)
    for (doc, expected_valid), (_, message) in zip(structural_corpus(), [(None, ""), *CASES], strict=False):
        if any(tag in message for tag in SEMANTIC_ONLY) or "NaN" in json.dumps(doc):
            continue
        assert checker.is_valid(doc) == expected_valid, (message, doc)


def test_bundled_and_scaffold_incidents_validate_against_the_json_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    import yaml

    from regressleuth.scaffold import INCIDENT

    checker = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
    root = Path(__file__).resolve().parents[1]
    documents = [
        yaml.safe_load(INCIDENT),
        yaml.safe_load((root / "src/regressleuth/_demo/incident.yaml").read_text()),
    ]
    for folder in (
        "benchmarks/holdout/incidents",
        "benchmarks/higher_order/incidents",
        "examples/http_service",
    ):
        documents += [yaml.safe_load(p.read_text()) for p in (root / folder).glob("*.yaml")]
    for document in documents:
        assert validate(document) == [] and checker.is_valid(document), document.get("id")
