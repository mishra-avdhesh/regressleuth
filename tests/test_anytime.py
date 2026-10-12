"""``interval: anytime``: the diagnosis-level error bound and its declared-noise safeguard."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from regressleuth import Incident, investigate
from regressleuth.errors import InvalidIncident
from regressleuth.reporting import render_text
from regressleuth.spec import validate
from regressleuth.stats import anytime_radius

SCHEMA = Path(__file__).resolve().parents[1] / "src/regressleuth/schemas/result-1.0.schema.json"
COMPONENTS = ("a", "b", "c", "d", "e")


def spec(replay: dict[str, Any], components: tuple[str, ...] = COMPONENTS) -> dict[str, Any]:
    return {
        "version": "1.0",
        "id": "noisy",
        "good": {c: "old" for c in components},
        "bad": {c: "new" for c in components},
        "metric": {"name": "accuracy", "direction": "higher_is_better", "regression_threshold": 0.02},
        "replay": replay,
        "adapter": {"type": "python", "callable": "module:function"},
    }


def noisy_runner(sd: float, cause: frozenset[str] = frozenset({"b", "d"})) -> Any:
    def run(state: dict[str, Any], _cases: Any, _metric: str, seed: int = 0) -> float:
        changed = frozenset(c for c, value in state.items() if value == "new")
        rng = random.Random(f"{sorted(changed)}:{seed}")
        return 0.9 - (0.05 if cause <= changed else 0.0) + rng.gauss(0, sd)

    return run


def test_radius_shrinks_with_runs_and_vanishes_without_noise() -> None:
    radii = [anytime_radius(n, 1.0, 0.01) for n in (1, 2, 5, 20, 100)]
    assert radii == sorted(radii, reverse=True)
    assert anytime_radius(10, 0.0, 0.01) == 0.0
    assert anytime_radius(0, 1.0, 0.01) == float("inf")
    assert anytime_radius(10, 1.0, 0.001) > anytime_radius(10, 1.0, 0.01)


def test_radius_covers_the_mean_at_every_stopping_time() -> None:
    """Ever-crossing frequency over 200 runs stays below alpha for Gaussian noise."""
    rng = random.Random(0)
    alpha, trials, crossed = 0.1, 2000, 0
    for _ in range(trials):
        total = 0.0
        for n in range(1, 201):
            total += rng.gauss(0, 1)
            if abs(total / n) > anytime_radius(n, 1.0, alpha):
                crossed += 1
                break
    assert crossed / trials < alpha


def test_anytime_requires_a_declared_noise_scale(tmp_path: Path) -> None:
    assert any("noise_scale: required" in p for p in validate(spec({"interval": "anytime"})))
    assert any("applies only to interval: anytime" in p for p in validate(spec({"noise_scale": 0.01})))
    assert any("at least 0" in p for p in validate(spec({"interval": "anytime", "noise_scale": -1})))
    assert validate(spec({"interval": "anytime", "noise_scale": 0.01})) == []
    with pytest.raises(InvalidIncident, match=r"specification 1\.0"):
        Incident.from_spec(spec({"interval": "anytime"}), base_dir=tmp_path)
    incident = Incident.from_spec(spec({"interval": "anytime", "noise_scale": 0}), base_dir=tmp_path)
    assert incident.replay.noise_scale == 0.0


def test_correct_declaration_verifies_with_the_bound_in_the_report(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    incident = Incident.from_spec(
        spec({"interval": "anytime", "noise_scale": 0.005, "repeats": 3, "max_repeats": 12}),
        base_dir=tmp_path,
    )
    report = investigate(incident, executor=noisy_runner(0.005), budget=32)
    assert report.status == "verified" and report.diagnosis == ("b", "d")
    data = report.to_dict()
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(data)
    assert data["verification"]["diagnosis_error_bound"] == pytest.approx(0.05)
    assert data["verification"]["interval_method"] == "anytime"
    assert data["verification"]["assumption_checks"]["noise"] == "assumed"
    good_runs = report.experiments[0].runs
    assert good_runs == 12  # the shared baseline gets all of its runs at once
    assert "P(verified set is not a true minimal failing set) <= 0.05" in render_text(report)


def test_misdeclared_noise_withholds_verified(tmp_path: Path) -> None:
    incident = Incident.from_spec(
        spec({"interval": "anytime", "noise_scale": 0.001, "repeats": 3, "max_repeats": 12}),
        base_dir=tmp_path,
    )
    report = investigate(incident, executor=noisy_runner(0.01), budget=32)
    assert report.status != "verified"
    assert report.confidence_meta["noise_check"]["status"] == "violated"
    assert report.to_dict()["verification"]["assumption_checks"]["noise"] == "violated"


def test_zero_noise_scale_is_the_deterministic_rule(tmp_path: Path) -> None:
    incident = Incident.from_spec(spec({"interval": "anytime", "noise_scale": 0}), base_dir=tmp_path)
    report = investigate(incident, executor=noisy_runner(0.0), budget=32)
    assert report.status == "verified" and report.diagnosis == ("b", "d")
    assert report.total_runs == len(report.experiments)
    assert report.confidence_meta["noise_check"]["status"] == "not_checked"


def test_single_component_reports_that_every_state_was_replayed(tmp_path: Path) -> None:
    incident = Incident.from_spec(spec({}, components=("lib",)), base_dir=tmp_path)
    report = investigate(incident, executor=noisy_runner(0.0, frozenset({"lib"})), budget=4)
    assert report.status == "verified"
    assert "every combination was replayed" in report.reason
    checks = report.to_dict()["verification"]["assumption_checks"]
    assert checks["monotone_failure"] == "checked"
