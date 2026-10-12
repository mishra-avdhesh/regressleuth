"""File-free entry point: diagnose a regression from a plain Python function."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .adapters import PythonCallableAdapter
from .engine import investigate
from .models import Incident, InvestigationReport


def diagnose(
    good: dict[str, Any],
    bad: dict[str, Any],
    run: Callable[..., float],
    *,
    threshold: float = 0.05,
    direction: str = "higher_is_better",
    metric: str = "metric",
    budget: int = 16,
    strategy: str = "adaptive",
    repeats: int = 1,
    max_repeats: int | None = None,
    confidence: float = 0.95,
    seed: int = 0,
    audit: int | str = "extended",
    interval: str | None = None,
    noise_scale: float | None = None,
    max_cause_size: int = 2,
    timeout_seconds: float | None = None,
    name: str = "diagnosis",
) -> InvestigationReport:
    """Find the smallest set of changed components that reproduces a regression.

    ``good`` and ``bad`` map component names to JSON-serializable versions (a path, a git SHA,
    a config dict). ``run(components)`` receives a dict with the same keys, each holding its
    good or bad version, and returns the metric measured on your fixed evaluation cases.
    If ``run`` accepts a ``seed`` keyword it gets the repeat index, and ``repeats`` /
    ``max_repeats`` enable confidence-based judgement of noisy metrics. ``threshold`` is the
    change that counts as a regression; ``direction`` is ``higher_is_better`` (default) or
    ``lower_is_better`` (``"higher"``/``"lower"`` are accepted too).

    Noisy runs are judged by per-comparison Student-t intervals and end at most ``inferred``.
    Pass ``noise_scale`` (an upper bound on one run's noise, as a sub-Gaussian scale) to use
    ``interval="anytime"``, where ``verified`` carries P(wrong verified) <= 1 - confidence.

    >>> report = diagnose({"model": "v1", "prep": "p1"}, {"model": "v2", "prep": "p2"}, run)
    >>> print(report.summary())
    """
    adapter = PythonCallableAdapter(run, timeout_seconds=timeout_seconds)
    top = max_repeats or repeats
    if top > 1 and not adapter.accepts_seed:
        raise ValueError("repeats > 1 requires run(components, seed) to accept a seed")
    direction = {"higher": "higher_is_better", "lower": "lower_is_better"}.get(direction, direction)
    document = {
        "version": "1.0",
        "id": name,
        "good": good,
        "bad": bad,
        "metric": {"name": metric, "direction": direction, "regression_threshold": threshold},
        "replay": {
            "repeats": repeats,
            "max_repeats": top,
            "confidence": confidence,
            "interval": interval or ("anytime" if noise_scale is not None else "student_t"),
            **({"noise_scale": noise_scale} if noise_scale is not None else {}),
        },
        "search": {"strategy": strategy, "max_cause_size": max_cause_size, "seed": seed},
        "budget": {"max_replays": budget, "audit": audit},
        "adapter": {"type": "python", "callable": "in_process:run"},
    }
    incident = Incident.from_spec(document, base_dir=".")
    return investigate(incident, executor=adapter)
