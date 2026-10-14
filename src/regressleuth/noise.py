"""Estimate a ``noise_scale`` for ``interval: anytime`` from calibration runs of the good state.

``interval: anytime`` needs an upper bound on one run's noise. Declaring the sample SD of a
few runs would understate it about half the time, so ``calibrate`` reports a one-sided
upper confidence bound for the SD: ``s * sqrt((n - 1) / chi2_quantile(1 - level, n - 1))``,
valid for Gaussian run-to-run noise. Calibration uses seeds that the diagnosis never uses
(by default 1000 and up), so the bound is not fitted to the replays it later judges. With
calibration level ``c`` and diagnosis confidence ``1 - alpha``, P(wrong ``verified``) is at
most ``alpha + (1 - c)`` under Gaussian noise.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from typing import Any

from .adapters import build_adapter
from .adapters.base import ReplayRequest
from .errors import InvalidIncident
from .models import Incident


def _lower_regularized_gamma(a: float, x: float) -> float:
    """P(a, x), the regularized lower incomplete gamma function."""
    if x <= 0:
        return 0.0
    if x < a + 1:  # series
        term = total = 1.0 / a
        n = a
        for _ in range(500):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    tiny = 1e-300  # continued fraction for the upper tail (Lentz)
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return 1.0 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_quantile(probability: float, df: int) -> float:
    """Inverse CDF of the chi-square distribution, by bisection."""
    if not 0 < probability < 1 or df < 1:
        raise ValueError("probability must be in (0, 1) and df at least 1")
    low, high = 0.0, max(10.0, 10.0 * df)
    while _lower_regularized_gamma(df / 2, high / 2) < probability:
        high *= 2
    for _ in range(200):
        middle = (low + high) / 2
        if _lower_regularized_gamma(df / 2, middle / 2) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def sd_upper_bound(values: list[float], level: float = 0.99) -> float:
    """One-sided ``level`` upper confidence bound for the SD of Gaussian values."""
    if len(values) < 2:
        raise ValueError("need at least two calibration runs")
    sd = statistics.stdev(values)
    n = len(values)
    return sd * math.sqrt((n - 1) / chi2_quantile(1 - level, n - 1))


def calibrate(
    incident: Incident,
    *,
    runs: int = 10,
    level: float = 0.99,
    seed_offset: int = 1000,
    executor: Callable[..., float] | None = None,
) -> dict[str, Any]:
    """Run the good state ``runs`` times and suggest a ``noise_scale``."""
    if runs < 3:
        raise InvalidIncident("use at least three calibration runs")
    if not 0 < level < 1:
        raise InvalidIncident("calibration level must be strictly between 0 and 1")
    values = []
    if executor is not None:
        for index in range(runs):
            values.append(
                float(
                    executor(
                        dict(incident.good),
                        incident.replay.cases,
                        incident.replay.metric,
                        seed=seed_offset + index,
                    )
                )
            )
    else:
        adapter = build_adapter(incident)
        try:
            for index in range(runs):
                outcome = adapter.replay(
                    ReplayRequest(
                        dict(incident.good),
                        seed_offset + index,
                        incident.replay.metric,
                        incident.replay.cases,
                    )
                )
                if outcome.status != "ok" or outcome.metric is None:
                    raise InvalidIncident(
                        f"calibration run {index + 1} did not produce a metric ({outcome.status})"
                    )
                values.append(float(outcome.metric))
        finally:
            adapter.close()
    sd = statistics.stdev(values)
    if sd == 0:
        raise InvalidIncident(
            "calibration runs showed no variation, so no positive noise_scale can be estimated; "
            "use deterministic replay or supply a justified positive bound"
        )
    bound = sd_upper_bound(values, level)
    return {
        "runs": runs,
        "seeds": [seed_offset, seed_offset + runs - 1],
        "mean": statistics.fmean(values),
        "sd": sd,
        "level": level,
        "noise_scale": bound,
        "threshold_to_noise": incident.replay.regression_threshold / bound if bound > 0 else math.inf,
    }
