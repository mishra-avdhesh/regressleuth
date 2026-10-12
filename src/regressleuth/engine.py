"""Strategy-independent diagnosis under an explicit minimal-conjunction model."""

from __future__ import annotations

import itertools
import math
import random
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from .adapters import Adapter, build_adapter
from .errors import IncompatibleReplay, InvalidIncident
from .models import Experiment, Incident, InvestigationReport
from .redact import redact_state
from .stats import anytime_radius, t_quantile, welch_df
from .strategies import STRATEGIES, Context, Hypothesis, candidate_causes, make_strategy

Evaluator = Callable[..., float]
LEGACY_DEFAULT_BUDGET = 8


def _ordered(hypotheses: set[Hypothesis]) -> list[Hypothesis]:
    return sorted(hypotheses, key=lambda h: (len(h), tuple(sorted(h))))


def _requirements(candidate: Hypothesis) -> list[Hypothesis]:
    """The candidate itself, then every non-empty proper subset (smallest first)."""
    proper = [
        frozenset(subset)
        for size in range(1, len(candidate))
        for subset in itertools.combinations(sorted(candidate), size)
    ]
    return [candidate, *proper]


def _audit_masks(candidate: Hypothesis, components: tuple[str, ...], extended: bool) -> list[Hypothesis]:
    """Replays that test the monotone model beyond minimality.

    Removing a cause component from the all-bad state must restore a pass, and adding any
    further bad component to the cause must keep the failure (the frozen ``full`` audit).
    ``extended`` also checks, away from the candidate, that (a) adding any *pair* of further
    components keeps the failure, and (b) every single other component and every pair of
    other components passes on its own. (b) exposes latent failures elsewhere that a
    cancelling or healing change hides in the all-bad state.
    """
    full = frozenset(components)
    others = sorted(full - candidate)
    masks = [full - {component} for component in sorted(candidate)]
    masks += [candidate | {component} for component in others]
    if extended:
        masks += [candidate | set(pair) for pair in itertools.combinations(others, 2)]
        masks += [frozenset((component,)) for component in others]
        masks += [frozenset(pair) for pair in itertools.combinations(others, 2)]
    unique: list[Hypothesis] = []
    for mask in masks:
        if mask and mask != full and mask not in unique:
            unique.append(mask)
    return unique


def investigate(
    incident: Incident | str | Path,
    *,
    budget: int | None = None,
    strategy: str | None = None,
    executor: Evaluator | None = None,
    seed: int | None = None,
    audit: int | str | None = None,
    max_cause_size: int | None = None,
) -> InvestigationReport:
    """Investigate a regression using at most ``budget`` isolation replays.

    ``budget`` counts the two endpoint replays, search replays and minimality
    verification replays. Each replay may run the evaluator several times when the
    incident declares ``repeats`` (noisy metrics); a replay is judged by a
    confidence rule and can end ``inconclusive`` when noise hides the effect.

    A cause is ``verified`` only when its own mask fails, every proper subset
    passes, and the monotonicity audit (extra replays: ``"full"``, ``"extended"``,
    an integer cap, or ``0`` to skip) found no contradiction. A unique cause without
    a complete audit is ``inferred``. A contradiction anywhere ends as
    ``assumption_violated`` and no cause is reported.

    Arguments left as ``None`` come from the incident's ``search``/``budget`` sections
    (specification 1.0) or the incident object's defaults (budget 8, adaptive, seed 0,
    extended audit, causes of at most two components). Frozen benchmark helpers select
    the historical full audit explicitly.

    All strategies share this driver, so caching, budget accounting, hypothesis
    elimination and the verification rule are identical; strategies differ only
    in which replay they request next.
    """
    if not isinstance(incident, Incident):
        incident = Incident.from_file(incident)
    declared = incident.search
    budget = budget if budget is not None else (declared.budget or LEGACY_DEFAULT_BUDGET)
    strategy = strategy if strategy is not None else declared.strategy
    seed = seed if seed is not None else declared.seed
    audit = audit if audit is not None else declared.audit
    max_cause_size = max_cause_size if max_cause_size is not None else declared.max_cause_size
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 2:
        raise InvalidIncident("budget must be an integer of at least 2")
    if strategy not in STRATEGIES:
        raise InvalidIncident(f"strategy must be one of {', '.join(STRATEGIES)}")
    if audit not in ("full", "extended") and (
        isinstance(audit, bool) or not isinstance(audit, int) or audit < 0
    ):
        raise InvalidIncident("audit must be 'full', 'extended' or a non-negative integer")
    if max_cause_size not in (1, 2, 3):
        raise InvalidIncident("max_cause_size must be 1, 2 or 3")
    components = incident.changed_components
    if len(components) > 12:
        raise InvalidIncident("at most 12 changed components are supported")
    spec = incident.replay
    noisy = spec.max_repeats > 1
    anytime = spec.interval == "anytime"
    # Error budget for ``anytime``: split over every mask that could ever be replayed (2^k,
    # including the good baseline), so the bound survives adaptive mask choice and stopping.
    per_mask_alpha = (1 - spec.confidence) / 2 ** len(components)
    owned = executor is None
    evaluator: Evaluator = executor if executor is not None else build_adapter(incident)
    started_at = time.perf_counter()
    hypotheses = candidate_causes(components, max_cause_size)
    report = InvestigationReport(
        incident_id=incident.id,
        status="unresolved",
        strategy=strategy,
        budget=budget,
        changed_components=components,
        incident_meta={
            "spec_version": incident.spec_version,
            "description": incident.description,
            "unchanged_components": list(incident.unchanged_components),
            "states": {
                "values": incident.report_values,
                "good": redact_state(incident.good, incident.report_values),
                "bad": redact_state(incident.bad, incident.report_values),
            },
            "metric": {
                "name": spec.metric,
                "direction": "higher_is_better" if spec.direction == "higher" else "lower_is_better",
                "regression_threshold": spec.regression_threshold,
            },
        },
        search_meta={
            "seed": seed,
            "max_cause_size": max_cause_size,
            "hypothesis_count": len(hypotheses),
            "search_space": 2 ** len(components),
            "audit": audit,
        },
        confidence_meta={
            "level": spec.confidence,
            "repeats": spec.repeats,
            "max_repeats": spec.max_repeats,
            "interval": spec.interval,
            "interval_applied": noisy or anytime,
            "rule": (
                "anytime-valid confidence sequences (sub-Gaussian normal mixture) for every mask mean, "
                f"error {1 - spec.confidence:.3g} split over {2 ** len(components)} masks"
                if anytime
                else f"{spec.interval.replace('_', '-')} confidence interval on the difference from the good baseline"
                if noisy
                else "deterministic threshold comparison"
            ),
            "noise_scale": spec.noise_scale,
            "diagnosis_error_bound": round(1 - spec.confidence, 12) if anytime else None,
        },
        adapter_meta=evaluator.describe() if isinstance(evaluator, Adapter) else {"type": "callable"},
    )
    observations: dict[Hypothesis, str] = {}
    samples: dict[Hypothesis, list[float]] = {}
    sign = 1.0 if spec.direction == "higher" else -1.0
    empty = frozenset[str]()
    full = frozenset(components)

    def classify(mask: Hypothesis) -> str:
        if mask == empty:
            return "pass"
        good, other = samples[empty], samples[mask]
        effect = sign * (statistics.fmean(good) - statistics.fmean(other))
        if anytime:
            scale = spec.noise_scale or 0.0
            margin = anytime_radius(len(good), scale, per_mask_alpha) + anytime_radius(
                len(other), scale, per_mask_alpha
            )
            if effect - margin >= spec.regression_threshold - 1e-12:
                return "fail"
            if effect + margin < spec.regression_threshold - 1e-12:
                return "pass"
            return "inconclusive"
        variance = 0.0
        for values in (good, other):
            if len(values) > 1:
                variance += statistics.variance(values) / len(values)
        if spec.interval == "student_t" and variance > 0:
            df = welch_df(
                statistics.variance(good) if len(good) > 1 else 0.0,
                len(good),
                statistics.variance(other) if len(other) > 1 else 0.0,
                len(other),
            )
            quantile = t_quantile((1 + spec.confidence) / 2, df) if math.isfinite(df) else spec.confidence_z
        else:
            quantile = spec.confidence_z  # frozen default: normal interval
        margin = quantile * math.sqrt(variance)
        if effect - margin >= spec.regression_threshold - 1e-12:
            return "fail"
        if effect + margin < spec.regression_threshold - 1e-12:
            return "pass"
        return "inconclusive"

    def run(mask: Hypothesis, role: str) -> str:
        nonlocal hypotheses
        started = time.perf_counter()
        values = samples.setdefault(mask, [])
        outcome = "error"
        error_kind: str | None = None
        # every ``anytime`` comparison shares the good baseline, so it gets all its runs at once
        step = spec.max_repeats if anytime and mask == empty else spec.repeats
        while True:
            try:
                for _ in range(step):
                    index = len(values)
                    state = incident.selected_state(mask)
                    value = (
                        evaluator(state, spec.cases, spec.metric, seed=index)
                        if noisy
                        else evaluator(state, spec.cases, spec.metric)
                    )
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(value)
                    ):
                        raise ValueError("replay metric must be a finite number")
                    values.append(float(value))
            except IncompatibleReplay:
                outcome = "incompatible"
                break
            except Exception as exc:  # noqa: BLE001 - runner failures of any kind are recorded, not leaked
                outcome = "error"
                error_kind = getattr(
                    exc, "kind", "invalid_metric" if isinstance(exc, ValueError) else "exception"
                )
                break
            outcome = classify(mask)
            if outcome == "inconclusive" and len(values) < spec.max_repeats:
                step = min(spec.repeats, spec.max_repeats - len(values))
                continue
            break
        usable = outcome in {"pass", "fail", "inconclusive"}
        observations[mask] = outcome
        if outcome in {"pass", "fail"}:
            hypotheses = {
                hypothesis
                for hypothesis in hypotheses
                if ("fail" if hypothesis <= mask else "pass") == outcome
            }
        report.experiments.append(
            Experiment(
                changed=tuple(sorted(mask)),
                outcome=outcome,  # type: ignore[arg-type]
                metric=statistics.fmean(values) if usable and values else None,
                duration_seconds=time.perf_counter() - started,
                role=role,  # type: ignore[arg-type]
                runs=len(values),
                metric_sd=statistics.stdev(values) if usable and len(values) > 1 else None,
                hypotheses_remaining=len(hypotheses),
                error_kind=error_kind,
            )
        )
        return outcome

    try:
        _search(
            report,
            run,
            observations,
            hypotheses_ref=lambda: hypotheses,
            components=components,
            strategy=strategy,
            seed=seed,
            budget=budget,
            audit=audit,
            empty=empty,
            full=full,
        )
    finally:
        report.runtime_seconds = time.perf_counter() - started_at
        if owned and isinstance(evaluator, Adapter):
            evaluator.close()
    if anytime:
        _check_declared_noise(report, samples, spec.noise_scale or 0.0)
    elif noisy and spec.interval == "student_t":
        _cap_unbounded_noise(report, samples)
    return report


def _cap_unbounded_noise(report: InvestigationReport, samples: dict[Hypothesis, list[float]]) -> None:
    """Noisy results judged by per-comparison intervals are capped at ``inferred``.

    Welch intervals bound one comparison at a time; across repeated looks and many masks
    they bound nothing for the diagnosis, and a pre-registered simulation produced wrong
    ``verified`` results with them (docs/VERIFICATION.md). ``verified`` therefore needs
    ``interval: anytime`` with a declared ``noise_scale``, unless the runs never varied.
    The explicit historical ``normal`` profile keeps its frozen behavior.
    """
    varied = any(len(values) >= 2 and statistics.stdev(values) > 0 for values in samples.values())
    report.confidence_meta["diagnosis_error_control"] = (
        "none: per-comparison intervals" if varied else "exact: no run-to-run variation observed"
    )
    if varied and report.status == "verified":
        report.status = "inferred"
        report.reason = (
            "minimal cause reproduced and the audit found no contradiction, but the noisy replays were "
            "judged by per-comparison intervals that bound no diagnosis-level error; declare "
            "replay.noise_scale and use interval: anytime to allow verified"
        )


def _check_declared_noise(
    report: InvestigationReport, samples: dict[Hypothesis, list[float]], scale: float
) -> None:
    """Withhold ``verified`` when the observed spread plainly contradicts ``noise_scale``.

    The error bound of ``interval: anytime`` assumes the declared scale. This check can
    only downgrade a result, so it never weakens the bound; it catches gross
    misdeclarations: a pooled within-mask SD above twice the scale with at least four
    degrees of freedom, or any variation when the scale is 0.
    """
    squares = 0.0
    freedom = 0
    for values in samples.values():
        if len(values) >= 2:
            mean = statistics.fmean(values)
            squares += sum((value - mean) ** 2 for value in values)
            freedom += len(values) - 1
    pooled = math.sqrt(squares / freedom) if freedom else 0.0
    violated = (scale == 0 and pooled > 0) or (freedom >= 4 and pooled > 2 * scale)
    if not violated:
        report.confidence_meta["noise_check"] = {
            "status": "consistent" if freedom else "not_checked",
            "detail": f"Pooled run-to-run SD {pooled:.4g} ({freedom} df) against noise_scale {scale}.",
        }
        return
    report.confidence_meta["noise_check"] = {
        "status": "violated",
        "detail": f"Pooled run-to-run SD {pooled:.4g} ({freedom} df) contradicts the declared "
        f"noise_scale {scale}.",
    }
    if report.status == "verified":
        report.status = "inferred"
        report.reason = (
            "minimal cause reproduced, but the observed noise contradicts the declared noise_scale, "
            "so the diagnosis-level error bound does not apply"
        )


def _search(
    report: InvestigationReport,
    run: Callable[[Hypothesis, str], str],
    observations: dict[Hypothesis, str],
    *,
    hypotheses_ref: Callable[[], set[Hypothesis]],
    components: tuple[str, ...],
    strategy: str,
    seed: int,
    budget: int,
    audit: int | str,
    empty: Hypothesis,
    full: Hypothesis,
) -> None:
    if run(empty, "baseline") != "pass":
        report.status = "evaluation_error"
        report.reason = "known-good baseline replay failed"
        report.candidates = [tuple(sorted(h)) for h in _ordered(hypotheses_ref())]
        return
    bad_outcome = run(full, "baseline")
    if bad_outcome in {"error", "incompatible"}:
        report.status = "evaluation_error"
        report.reason = "failing baseline replay could not be evaluated"
        return
    if bad_outcome == "inconclusive":
        report.status = "inconclusive"
        report.reason = (
            "known-bad state could not be separated from known-good under the declared noise; "
            "raise repeats or max_repeats"
        )
        return
    if bad_outcome != "fail":
        report.status = "invalid_baseline"
        report.reason = "known-bad state did not cross the regression threshold on the fixed cases"
        return

    ctx = Context(components, hypotheses_ref(), observations, random.Random(seed))
    exhaustive = strategy == "exhaustive"
    generator = make_strategy(strategy, ctx)
    started_generator = False

    def advance(outcome: str | None) -> Hypothesis | None:
        nonlocal started_generator
        try:
            if not started_generator:
                started_generator = True
                return next(generator)
            return generator.send(outcome or "")
        except StopIteration:
            return None

    last_outcome: str | None = None
    while len(report.experiments) < budget:
        hypotheses = hypotheses_ref()
        ctx.hypotheses = hypotheses
        if not hypotheses:
            break
        if len(hypotheses) == 1 and not exhaustive:
            missing = [m for m in _requirements(next(iter(hypotheses))) if m not in observations]
            if not missing:
                break
            if run(missing[0], "verification") == "error":
                report.status = "evaluation_error"
                report.reason = "a replay failed; no attribution was made"
                break
            continue
        pending = advance(last_outcome)
        if pending is None:
            report.reason = "no informative compatible replay remains"
            break
        last_outcome = run(pending, "search")
        if last_outcome == "error":
            report.status = "evaluation_error"
            report.reason = "a replay failed; no attribution was made"
            break

    hypotheses = hypotheses_ref()
    report.candidates = [tuple(sorted(h)) for h in _ordered(hypotheses)]
    if report.status == "evaluation_error":
        return
    size = report.search_meta.get("max_cause_size", 2)
    if not hypotheses:
        report.status = "assumption_violated"
        report.reason = (
            f"observations contradict every monotone cause of at most {size} components; no cause is reported"
        )
        return
    noisy_gap = any(
        e.outcome == "inconclusive" for e in report.experiments if e.role in {"search", "verification"}
    )
    if len(hypotheses) > 1:
        if noisy_gap:
            report.status = "inconclusive"
            report.reason = "noise left replays undecided and several causes remain compatible"
        else:
            report.reason = (
                "replay budget exhausted with multiple compatible causes"
                if len(report.experiments) >= budget
                else "strategy finished with multiple compatible causes"
            )
        return

    candidate = next(iter(hypotheses))
    requirements = _requirements(candidate)
    minimal = observations.get(candidate) == "fail" and all(
        observations.get(proper) == "pass" for proper in requirements[1:]
    )
    if not minimal:
        report.diagnosis = tuple(sorted(candidate))
        report.status = "inferred"
        report.reason = "unique compatible cause; direct minimality checks are incomplete"
        return

    planned = _audit_masks(candidate, components, extended=audit == "extended")
    allowance = len(planned) if audit in ("full", "extended") else int(audit)
    ran = 0
    if allowance > 0:
        for mask in planned:
            if mask not in observations and ran < allowance:
                outcome = run(mask, "audit")
                ran += 1
                if outcome == "error":
                    break
    expected = {m: ("fail" if candidate <= m else "pass") for m in planned}
    seen = {m: observations[m] for m in planned if observations.get(m) in {"pass", "fail"}}
    violations = [m for m, outcome in seen.items() if outcome != expected[m]]
    report.audit = {
        "enabled": allowance > 0 or audit in ("full", "extended"),
        "level": audit,
        "required": len(planned),
        "confirmed": sum(seen[m] == expected[m] for m in seen),
        "extra_replays": ran,
        "violations": [
            {"changed": sorted(m), "expected": expected[m], "observed": seen[m]} for m in violations
        ],
    }
    if violations:
        report.status = "assumption_violated"
        report.audit["suspected_cause"] = sorted(candidate)
        report.reason = (
            "an audit replay contradicts the monotone cause model; the suspected cause "
            "is withheld because other combinations behave differently"
        )
        return
    report.diagnosis = tuple(sorted(candidate))
    if audit == 0 or report.audit["confirmed"] == report.audit["required"]:
        report.status = "verified"
        report.reason = (
            "minimal cause reproduced on the fixed cases"
            if audit == 0
            else "minimal cause reproduced; every combination was replayed, so no audit replay was needed"
            if not planned
            else "minimal cause reproduced and the monotone model survived the audit"
        )
        report.audit["enabled"] = audit != 0
    else:
        report.status = "inferred"
        report.reason = (
            f"minimal cause reproduced, but only {report.audit['confirmed']} of "
            f"{report.audit['required']} audit replays are conclusive"
        )
