"""Calibration of noise_scale: chi-square quantiles, the SD upper bound and the helper."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from regressleuth import Incident
from regressleuth.cli import DEMO_DIR, main
from regressleuth.errors import InvalidIncident
from regressleuth.noise import calibrate, chi2_quantile, sd_upper_bound


@pytest.mark.parametrize(
    ("probability", "df", "expected"),
    [(0.01, 9, 2.0879), (0.05, 9, 3.3251), (0.95, 1, 3.8415), (0.5, 30, 29.3360), (0.99, 4, 13.2767)],
)
def test_chi2_quantiles_match_tables(probability: float, df: int, expected: float) -> None:
    assert chi2_quantile(probability, df) == pytest.approx(expected, abs=2e-4)


def test_upper_bound_covers_the_true_sd_at_its_level() -> None:
    rng = random.Random(1)
    misses = sum(sd_upper_bound([rng.gauss(0, 2.0) for _ in range(10)], 0.99) < 2.0 for _ in range(4000))
    assert misses / 4000 < 0.02  # nominal 1%


def test_calibrate_uses_separate_seeds_and_suggests_a_scale(tmp_path: Path) -> None:
    incident = Incident.from_spec(
        {
            "version": "1.0",
            "id": "noisy",
            "good": {"model": "v1"},
            "bad": {"model": "v2"},
            "metric": {"name": "accuracy", "direction": "higher_is_better", "regression_threshold": 0.02},
            "adapter": {"type": "python", "callable": "m:f"},
        },
        base_dir=tmp_path,
    )
    seeds: list[int] = []

    def run(state: dict[str, str], _cases: object, _metric: str, seed: int = 0) -> float:
        seeds.append(seed)
        return 0.9 + random.Random(seed).gauss(0, 0.004)

    found = calibrate(incident, runs=12, executor=run)
    assert seeds == list(range(1000, 1012))
    assert found["noise_scale"] > found["sd"] > 0
    assert found["threshold_to_noise"] == pytest.approx(0.02 / found["noise_scale"])
    with pytest.raises(InvalidIncident, match="strictly between 0 and 1"):
        calibrate(incident, level=1.0, executor=run)

    def constant(_state: dict[str, str], _cases: object, _metric: str, seed: int = 0) -> float:
        return 0.9

    with pytest.raises(InvalidIncident, match="no positive noise_scale"):
        calibrate(incident, executor=constant)


def test_invalid_calibration_level_is_a_cli_input_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["noise-scale", str(DEMO_DIR / "incident.yaml"), "--level", "1"]) == 3
    assert "calibration level must be strictly between 0 and 1" in capsys.readouterr().err
