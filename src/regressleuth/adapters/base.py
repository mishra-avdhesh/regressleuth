"""The replay contract every adapter implements.

An adapter turns one *replay request* (a mapping from component name to the chosen good or
bad version, a run seed, the metric name and the fixed cases) into one *replay outcome*:
a finite metric, ``incompatible`` (the hybrid cannot be built) or an error with a kind.
Adapters never retry and never decide pass or fail; the engine does the counting and
judging, so budget accounting is identical whichever adapter is used.
"""

from __future__ import annotations

import math
import platform
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal

from ..errors import IncompatibleReplay, ReplayError

HISTORY_LIMIT = 512


@dataclass(frozen=True)
class ReplayRequest:
    components: dict[str, Any]
    seed: int = 0
    metric: str = "metric"
    cases: Path | None = None


@dataclass
class ReplayOutcome:
    status: Literal["ok", "incompatible", "error"]
    metric: float | None = None
    error_kind: str | None = None
    message: str = ""
    duration_seconds: float = 0.0
    stdout_tail: str = ""
    stderr_tail: str = ""
    seed: int = 0
    components: dict[str, Any] = field(default_factory=dict)


def finite_metric(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ReplayError("replay metric must be a finite number", kind="invalid_metric")
    return float(value)


def runtime_metadata() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": sys.platform,
    }


class Adapter(ABC):
    """Base class. Instances are also callables with the engine's evaluator signature."""

    kind: ClassVar[str] = "adapter"

    def __init__(self) -> None:
        self.history: list[ReplayOutcome] = []

    @abstractmethod
    def replay(self, request: ReplayRequest) -> ReplayOutcome:
        """Evaluate one hybrid. Must not raise for replay failures; return an outcome."""

    def describe(self) -> dict[str, Any]:
        """Reproducibility metadata for reports. Must never include secret values."""
        return {"type": self.kind, "runtime": runtime_metadata()}

    def close(self) -> None:  # noqa: B027 - optional hook, deliberately a no-op by default
        """Release resources (connections, temporary files)."""

    def __call__(self, state: dict[str, Any], cases: Path | None, metric: str, seed: int = 0) -> float:
        outcome = self.replay(ReplayRequest(state, seed, metric, cases))
        outcome.seed = seed
        outcome.components = state
        if len(self.history) < HISTORY_LIMIT:
            self.history.append(outcome)
        if outcome.status == "ok":
            return finite_metric(outcome.metric)
        if outcome.status == "incompatible":
            raise IncompatibleReplay(outcome.message or "hybrid is incompatible")
        raise ReplayError(outcome.message or "replay failed", kind=outcome.error_kind or "error")


def portable(text: str) -> str:
    """Keep relative paths; reduce absolute paths to '.../<name>' so reports carry no local paths."""
    if text.startswith("/") or (len(text) > 2 and text[1] == ":" and text[2] in "\\/"):
        return ".../" + text.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return text


def tail(data: bytes, limit: int) -> str:
    return data[-limit:].decode("utf-8", errors="replace") if limit > 0 else ""
