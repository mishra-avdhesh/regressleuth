"""Validated incident and evidence models."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Any, Literal

from .errors import InvalidIncident

Outcome = Literal["pass", "fail", "inconclusive", "incompatible", "error"]
DiagnosisStatus = Literal[
    "verified",
    "inferred",
    "inconclusive",
    "unresolved",
    "assumption_violated",
    "invalid_baseline",
    "evaluation_error",
]
STATUSES: tuple[str, ...] = (
    "verified",
    "inferred",
    "inconclusive",
    "unresolved",
    "assumption_violated",
    "invalid_baseline",
    "evaluation_error",
)
RESULT_SCHEMA = "regressleuth.result"
RESULT_SCHEMA_VERSION = "1.0"


def check_noise_scale(interval: str, value: Any) -> float | None:
    """``noise_scale`` is required by, and only meaningful for, ``interval: anytime``."""
    if interval != "anytime":
        if value is not None:
            raise InvalidIncident("replay.noise_scale applies only to interval: anytime")
        return None
    if value is None:
        raise InvalidIncident(
            "replay.noise_scale is required with interval: anytime (an upper bound on the "
            "sub-Gaussian scale of one run's metric noise; 0 for deterministic replays)"
        )
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise InvalidIncident("replay.noise_scale must be a finite number of at least 0")
    return float(value)


def _object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise InvalidIncident(f"{field_name} must be an object with string keys")
    return value


def _keys(value: dict[str, Any], allowed: set[str], required: set[str], field_name: str) -> None:
    extra = sorted(value.keys() - allowed)
    missing = sorted(required - value.keys())
    if extra or missing:
        raise InvalidIncident(f"{field_name}: unexpected keys {extra}; missing keys {missing}")


@dataclass(frozen=True)
class ReplaySpec:
    command: tuple[str, ...]
    cases: Path | None
    metric: str
    direction: Literal["higher", "lower"]
    regression_threshold: float
    timeout_seconds: float
    repeats: int = 1
    max_repeats: int = 1
    confidence_z: float = 1.96
    interpreter_component: str | None = None
    interpreters: tuple[tuple[str, str], ...] = ()
    confidence: float = 0.95
    interval: str = "student_t"
    # declared sub-Gaussian scale of one run's metric noise; required by ``interval: anytime``
    noise_scale: float | None = None

    def interpreter_for(self, state: dict[str, Any]) -> str | None:
        if self.interpreter_component is None:
            return None
        lookup = dict(self.interpreters)
        return lookup[state[self.interpreter_component]]


@dataclass(frozen=True)
class SearchConfig:
    """Search defaults declared by an incident; explicit call arguments override them."""

    strategy: str = "adaptive"
    max_cause_size: int = 2
    seed: int = 0
    budget: int | None = None
    audit: int | str = "extended"


@dataclass(frozen=True)
class Incident:
    id: str
    good: dict[str, Any]
    bad: dict[str, Any]
    replay: ReplaySpec
    base_dir: Path
    spec_version: str = "legacy"
    description: str = ""
    adapter: dict[str, Any] | None = None
    search: SearchConfig = field(default_factory=SearchConfig)
    report_values: str = "omit"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def changed_components(self) -> tuple[str, ...]:
        return tuple(sorted(key for key in self.good if self.good[key] != self.bad[key]))

    @property
    def unchanged_components(self) -> tuple[str, ...]:
        return tuple(sorted(key for key in self.good if self.good[key] == self.bad[key]))

    def selected_state(self, changed: frozenset[str]) -> dict[str, Any]:
        if not changed.issubset(self.changed_components):
            raise InvalidIncident("replay mask contains an unchanged or unknown component")
        return {key: deepcopy(self.bad[key] if key in changed else self.good[key]) for key in self.good}

    @classmethod
    def from_file(cls, path: str | Path) -> Incident:
        from .spec import load_document

        source = Path(path).resolve()
        raw = load_document(source)
        if isinstance(raw, dict) and "version" in raw:
            return cls.from_spec(raw, base_dir=source.parent)
        return cls.from_mapping(raw, base_dir=source.parent)

    @classmethod
    def from_spec(cls, raw: Any, *, base_dir: str | Path = ".") -> Incident:
        """Build from an Incident Specification 1.0 document (see docs/INCIDENT_SPEC.md)."""
        from .spec import DIRECTIONS, validate

        problems = validate(raw)
        if problems:
            raise InvalidIncident(
                f"incident does not match specification 1.0 ({len(problems)} problem(s))", problems
            )
        base = Path(base_dir).resolve()
        values = json.loads(json.dumps({"good": raw["good"], "bad": raw["bad"]}))
        adapter = dict(raw["adapter"])
        cases: Path | None = None
        if "cases" in raw:
            cases = (base / raw["cases"]).resolve()
            if not cases.is_file():
                raise InvalidIncident(f"cases: file not found: {raw['cases']}")
        replay = raw.get("replay") or {}
        repeats = replay.get("repeats", 1)
        confidence = replay.get("confidence", 0.95)
        interp = adapter.get("interpreters")
        search = raw.get("search") or {}
        budget = raw.get("budget") or {}
        spec = ReplaySpec(
            command=tuple(adapter.get("command", ())) if adapter["type"] == "command" else (),
            cases=cases,
            metric=raw["metric"]["name"],
            direction=DIRECTIONS[raw["metric"]["direction"]],  # type: ignore[arg-type]
            regression_threshold=float(raw["metric"]["regression_threshold"]),
            timeout_seconds=float(adapter.get("timeout_seconds", 600)),
            repeats=repeats,
            max_repeats=replay.get("max_repeats", repeats),
            confidence_z=NormalDist().inv_cdf((1 + confidence) / 2),
            interpreter_component=interp["component"] if interp else None,
            interpreters=tuple(sorted(interp["map"].items())) if interp else (),
            confidence=float(confidence),
            interval=replay.get("interval", "student_t"),
            noise_scale=check_noise_scale(replay.get("interval", "student_t"), replay.get("noise_scale")),
        )
        return cls(
            id=raw["id"],
            good=values["good"],
            bad=values["bad"],
            replay=spec,
            base_dir=base,
            spec_version=raw["version"],
            description=raw.get("description", ""),
            adapter=adapter,
            search=SearchConfig(
                strategy=search.get("strategy", "adaptive"),
                max_cause_size=search.get("max_cause_size", 2),
                seed=search.get("seed", 0),
                budget=budget.get("max_replays", 16),
                audit=budget.get("audit", "extended"),
            ),
            report_values=(raw.get("report") or {}).get("values", "omit"),
            metadata=dict(raw.get("metadata") or {}),
        )

    @classmethod
    def from_mapping(cls, raw: Any, *, base_dir: str | Path = ".") -> Incident:
        """Legacy pre-1.0 JSON manifests (kept for the frozen development benchmark)."""
        value = _object(raw, "incident")
        _keys(value, {"id", "good", "bad", "replay"}, {"id", "good", "bad", "replay"}, "incident")
        incident_id = value["id"]
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise InvalidIncident("id must be a nonempty string")
        good = _object(value["good"], "good")
        bad = _object(value["bad"], "bad")
        if not good or good.keys() != bad.keys():
            raise InvalidIncident("good and bad must have the same nonempty component keys")
        if any(not key.strip() for key in good):
            raise InvalidIncident("component names must be nonempty")
        try:
            frozen_values = json.dumps({"good": good, "bad": bad}, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidIncident("component values must be finite JSON values") from exc
        copied_values = json.loads(frozen_values)
        good = copied_values["good"]
        bad = copied_values["bad"]
        if good == bad:
            raise InvalidIncident("good and bad have no changed components")

        replay = _object(value["replay"], "replay")
        required_keys = {"command", "cases", "metric", "direction", "regression_threshold", "timeout_seconds"}
        optional_keys = {"repeats", "max_repeats", "confidence", "interpreters", "interval", "noise_scale"}
        _keys(replay, required_keys | optional_keys, required_keys, "replay")
        command = replay["command"]
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) and part for part in command)
        ):
            raise InvalidIncident("replay.command must be a nonempty list of strings")
        if not isinstance(replay["cases"], str) or not replay["cases"]:
            raise InvalidIncident("replay.cases must be a nonempty path")
        base = Path(base_dir).resolve()
        cases = (base / replay["cases"]).resolve()
        if not cases.is_file():
            raise InvalidIncident(f"fixed evaluation cases do not exist: {cases.name}")
        metric = replay["metric"]
        if not isinstance(metric, str) or not metric.strip():
            raise InvalidIncident("replay.metric must be a nonempty string")
        direction = replay["direction"]
        if direction not in {"higher", "lower"}:
            raise InvalidIncident("replay.direction must be 'higher' or 'lower'")
        threshold = replay["regression_threshold"]
        timeout = replay["timeout_seconds"]
        for name, number in (("regression_threshold", threshold), ("timeout_seconds", timeout)):
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(number)
                or number <= 0
            ):
                raise InvalidIncident(f"{name} must be a positive finite number")
        repeats = replay.get("repeats", 1)
        max_repeats = replay.get("max_repeats", repeats)
        for name, count in (("repeats", repeats), ("max_repeats", max_repeats)):
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 1000:
                raise InvalidIncident(f"replay.{name} must be an integer from 1 to 1000")
        if max_repeats < repeats:
            raise InvalidIncident("replay.max_repeats must be at least replay.repeats")
        confidence = replay.get("confidence", 0.95)
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0.5 <= confidence < 1
        ):
            raise InvalidIncident("replay.confidence must be a number from 0.5 up to 1")
        interval = replay.get("interval", "student_t")
        if not isinstance(interval, str) or interval not in {"student_t", "normal", "anytime"}:
            raise InvalidIncident("replay.interval must be student_t, normal or anytime")
        noise_scale = check_noise_scale(interval, replay.get("noise_scale"))
        interpreter_component: str | None = None
        interpreters: tuple[tuple[str, str], ...] = ()
        if "interpreters" in replay:
            raw_interp = _object(replay["interpreters"], "replay.interpreters")
            _keys(raw_interp, {"component", "map"}, {"component", "map"}, "replay.interpreters")
            interpreter_component = raw_interp["component"]
            mapping = _object(raw_interp["map"], "replay.interpreters.map")
            if interpreter_component not in good or not all(
                isinstance(v, str) and v for v in mapping.values()
            ):
                raise InvalidIncident("replay.interpreters must name a component and string paths")
            used = {good[interpreter_component], bad[interpreter_component]}
            if not used <= set(mapping):
                raise InvalidIncident("replay.interpreters.map must cover the good and bad values")
            interpreters = tuple(sorted(mapping.items()))
        spec = ReplaySpec(
            command=tuple(command),
            cases=cases,
            metric=metric,
            direction=direction,
            regression_threshold=float(threshold),
            timeout_seconds=float(timeout),
            repeats=repeats,
            max_repeats=max_repeats,
            confidence_z=NormalDist().inv_cdf((1 + confidence) / 2),
            interpreter_component=interpreter_component,
            interpreters=interpreters,
            confidence=float(confidence),
            interval=interval,
            noise_scale=noise_scale,
        )
        return cls(id=incident_id, good=good, bad=bad, replay=spec, base_dir=base)


@dataclass(frozen=True)
class Experiment:
    changed: tuple[str, ...]
    outcome: Outcome
    metric: float | None
    duration_seconds: float
    role: Literal["baseline", "search", "verification", "audit"]
    runs: int = 1
    metric_sd: float | None = None
    hypotheses_remaining: int | None = None
    error_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed": list(self.changed),
            "outcome": self.outcome,
            "metric": self.metric,
            "metric_sd": self.metric_sd,
            "runs": self.runs,
            "duration_seconds": self.duration_seconds,
            "role": self.role,
            "hypotheses_remaining": self.hypotheses_remaining,
            "error_kind": self.error_kind,
        }


@dataclass
class InvestigationReport:
    incident_id: str
    status: DiagnosisStatus
    strategy: str
    budget: int
    changed_components: tuple[str, ...]
    experiments: list[Experiment] = field(default_factory=list)
    candidates: list[tuple[str, ...]] = field(default_factory=list)
    diagnosis: tuple[str, ...] | None = None
    reason: str = ""
    audit: dict[str, Any] = field(default_factory=dict)
    incident_meta: dict[str, Any] = field(default_factory=dict)
    search_meta: dict[str, Any] = field(default_factory=dict)
    confidence_meta: dict[str, Any] = field(default_factory=dict)
    adapter_meta: dict[str, Any] = field(default_factory=dict)
    runtime_seconds: float = 0.0

    @property
    def experiments_used(self) -> int:
        return len(self.experiments)

    @property
    def isolation_replays(self) -> int:
        """Replays spent on endpoints, search and minimality verification (no audit)."""
        return sum(experiment.role != "audit" for experiment in self.experiments)

    @property
    def total_runs(self) -> int:
        return sum(experiment.runs for experiment in self.experiments)

    @property
    def root_cause(self) -> tuple[str, ...] | None:
        return self.diagnosis if self.status == "verified" else None

    def summary(self) -> str:
        """Human-readable report for a terminal or notebook."""
        from .reporting import render_text

        return render_text(self)

    def to_markdown(self) -> str:
        from .reporting import render_markdown

        return render_markdown(self)

    def to_html(self) -> str:
        from .reporting import render_html

        return render_html(self)

    def _repr_html_(self) -> str:  # notebook display
        import html

        return f"<pre>{html.escape(self.summary())}</pre>"

    def _assumptions(self) -> list[dict[str, str]]:
        size = self.search_meta.get("max_cause_size", 2)
        audit = self.audit or {}
        violated = self.status == "assumption_violated"
        if violated:
            monotone = (
                "violated",
                "a replay contradicted the model (non-monotone failure, or a cause "
                f"larger than {size} components)",
            )
        elif audit.get("required"):
            done = audit.get("confirmed", 0) == audit["required"]
            monotone = (
                "checked" if done else "partially_checked",
                f"{audit.get('confirmed', 0)} of {audit['required']} audit replays confirmed",
            )
        elif audit and audit.get("enabled", True) and "required" in audit:
            monotone = (
                "checked",
                "every combination of the changed components was replayed; no audit replay was needed",
            )
        elif audit and not audit.get("enabled", True):
            monotone = ("not_checked", "the audit was disabled")
        else:
            monotone = ("not_checked", "no unique minimal cause was reached, so no audit ran")
        incompatible = sum(e.outcome == "incompatible" for e in self.experiments)
        repeats = self.confidence_meta.get("max_repeats", 1)
        return [
            {
                "id": "fixed_cohort",
                "status": "assumed",
                "statement": "Every replay scores the same labeled evaluation cases with the same metric.",
                "detail": "Not checkable by the tool; guaranteed by the adapter or runner.",
            },
            {
                "id": "declared_components_only",
                "status": "assumed",
                "statement": "A replay depends only on the declared component versions and the run seed.",
                "detail": "Undeclared changes (hardware, data drift inside a version) break attribution.",
            },
            {
                "id": "cause_size",
                "status": "violated" if violated else "assumed",
                "statement": f"The regression has one minimal cause of at most {size} components.",
                "detail": "Contradicted by the observations." if violated else "Not directly testable.",
            },
            {
                "id": "monotone_failure",
                "status": monotone[0],
                "statement": "Adding more bad components to the cause keeps the failure; removing a cause "
                "component from the bad state removes it.",
                "detail": monotone[1],
            },
            self._noise_assumption(repeats),
            {
                "id": "compatible_hybrids",
                "status": "checked",
                "statement": "Hybrids can be built; those that cannot are reported, never counted as passes.",
                "detail": f"{incompatible} incompatible replay(s)",
            },
        ]

    def _noise_assumption(self, repeats: int) -> dict[str, str]:
        meta = self.confidence_meta
        if meta.get("interval") == "anytime":
            check = meta.get("noise_check") or {}
            violated = check.get("status") == "violated"
            return {
                "id": "noise",
                "status": "violated" if violated else "assumed",
                "statement": f"Run-to-run metric noise is independent and {meta.get('noise_scale')}-sub-Gaussian "
                "(the declared noise_scale), so the diagnosis-level error bound applies.",
                "detail": check.get("detail", "")
                + f" Error bound for a verified diagnosis: {meta.get('diagnosis_error_bound')}.",
            }
        return {
            "id": "noise",
            "status": "handled" if repeats > 1 else "assumed",
            "statement": "Replays are deterministic, or their noise is captured by the declared repeats.",
            "detail": (
                f"repeats up to {repeats} at confidence {meta.get('level', 0.95)}; per-comparison "
                "intervals, no diagnosis-level error bound"
                + (
                    "; verified withheld because runs varied"
                    if meta.get("diagnosis_error_control", "").startswith("none")
                    else ""
                )
                if repeats > 1
                else "single run per replay"
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        from . import __version__

        kinds: dict[str, int] = {}
        for experiment in self.experiments:
            if experiment.error_kind:
                kinds[experiment.error_kind] = kinds.get(experiment.error_kind, 0) + 1
        assumptions = self._assumptions()
        verification = {
            "audit_mode": self.search_meta.get("audit"),
            "interval_method": self.confidence_meta.get("interval"),
            "interval_applied": self.confidence_meta.get("interval_applied", False),
            "confidence": self.confidence_meta.get("level"),
            "repeats": self.confidence_meta.get("repeats"),
            "max_repeats": self.confidence_meta.get("max_repeats"),
            "noise_scale": self.confidence_meta.get("noise_scale"),
            "diagnosis_error_bound": self.confidence_meta.get("diagnosis_error_bound"),
            "assumption_checks": {item["id"]: item["status"] for item in assumptions},
            "scope": "verified under the configured replay model, assumptions, and audit checks",
        }
        return {
            "schema": RESULT_SCHEMA,
            "schema_version": RESULT_SCHEMA_VERSION,
            "tool": {"name": "regressleuth", "version": __version__},
            "incident": {
                "id": self.incident_id,
                "changed_components": list(self.changed_components),
                **self.incident_meta,
            },
            "search": {"strategy": self.strategy, **self.search_meta},
            "status": self.status,
            "diagnosis": list(self.diagnosis) if self.diagnosis is not None else None,
            "suspected_cause": self.audit.get("suspected_cause"),
            "reason": self.reason,
            "alternatives": [list(candidate) for candidate in self.candidates],
            "replays": {
                "budget": self.budget,
                "isolation_used": self.isolation_replays,
                "audit_used": self.experiments_used - self.isolation_replays,
                "total": self.experiments_used,
                "runner_runs": self.total_runs,
            },
            "confidence": self.confidence_meta,
            "verification": verification,
            "assumptions": assumptions,
            "audit": self.audit,
            "experiments": [experiment.to_dict() for experiment in self.experiments],
            "errors": {
                "incompatible": sum(e.outcome == "incompatible" for e in self.experiments),
                "error": sum(e.outcome == "error" for e in self.experiments),
                "inconclusive": sum(e.outcome == "inconclusive" for e in self.experiments),
                "kinds": kinds,
            },
            "runtime_seconds": self.runtime_seconds,
            "adapter": self.adapter_meta,
        }
