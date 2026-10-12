"""Regressleuth Incident Specification, version 1.0.

The specification is documented in docs/INCIDENT_SPEC.md and mirrored as a JSON Schema in
``schemas/incident-1.0.schema.json``. ``validate`` reports every problem with its location
so all of them can be fixed at once. Nothing here depends on the benchmark.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from .errors import InvalidIncident

SPEC_VERSION = "1.0"
STRATEGY_NAMES = ("adaptive", "exhaustive", "random", "one_factor", "greedy", "ddmin")
DIRECTIONS = {"higher_is_better": "higher", "lower_is_better": "lower"}
HTTP_METRICS = ("accuracy", "error_rate", "mae", "rmse")
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
COMPONENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")
MAX_CHANGED = 12

TOP_KEYS = {
    "version",
    "id",
    "description",
    "good",
    "bad",
    "metric",
    "replay",
    "search",
    "budget",
    "adapter",
    "cases",
    "report",
    "metadata",
}
REQUIRED_TOP = {"version", "id", "good", "bad", "metric", "adapter"}
ADAPTER_KEYS = {
    "command": (
        {"type", "command", "cwd", "timeout_seconds", "env", "inherit_env", "interpreters", "capture_bytes"},
        {"type", "command"},
    ),
    "python": ({"type", "callable", "path", "timeout_seconds"}, {"type", "callable"}),
    "http": (
        {
            "type",
            "base_url",
            "mode",
            "path",
            "components_via",
            "header_name",
            "timeout_seconds",
            "batch_size",
            "headers",
            "input_field",
            "label_field",
            "prediction_field",
        },
        {"type", "base_url"},
    ),
    "docker": (
        {"type", "command", "image", "images", "timeout_seconds", "network", "docker"},
        {"type", "command"},
    ),
}


class _UniqueKeyLoader:  # built lazily so PyYAML stays an import-time detail
    loader: Any = None


def _yaml_loader() -> Any:
    if _UniqueKeyLoader.loader is None:
        import yaml

        class Loader(yaml.SafeLoader):
            pass

        def construct_mapping(loader: Any, node: Any, deep: bool = False) -> dict[Any, Any]:
            seen: set[Any] = set()
            for key_node, _ in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in seen:
                    raise yaml.constructor.ConstructorError(
                        None, None, f"duplicate key {key!r}", key_node.start_mark
                    )
                seen.add(key)
            return dict(loader.construct_mapping(node, deep))

        Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
        _UniqueKeyLoader.loader = Loader
    return _UniqueKeyLoader.loader


def load_document(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InvalidIncident(f"cannot read incident file: {path.name}") from exc
    if path.suffix.lower() in {".yaml", ".yml"}:
        import yaml

        try:
            return yaml.load(text, Loader=_yaml_loader())  # noqa: S506 - SafeLoader subclass
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            where = f" (line {mark.line + 1})" if mark is not None else ""
            problem = getattr(exc, "problem", None) or "invalid YAML"
            raise InvalidIncident(f"{path.name}: {problem}{where}") from exc
    try:
        return json.loads(text, object_pairs_hook=_no_duplicate_pairs)
    except ValueError as exc:
        raise InvalidIncident(f"{path.name}: invalid JSON ({exc})") from exc


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _integer(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)


def _finite_json(value: Any) -> bool:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def validate(doc: Any) -> list[str]:
    """Return a list of problems (empty when the document is a valid 1.0 incident)."""
    problems: list[str] = []
    add = problems.append
    if not isinstance(doc, dict):
        return ["(document): must be a mapping"]
    for key in sorted(set(doc) - TOP_KEYS):
        add(f"{key}: unknown key (allowed: {', '.join(sorted(TOP_KEYS))})")
    for key in sorted(REQUIRED_TOP - set(doc)):
        add(f"{key}: required")
    if "version" in doc and doc["version"] != SPEC_VERSION:
        add(f'version: must be the string "{SPEC_VERSION}" (got {doc["version"]!r})')
    if "id" in doc and not (isinstance(doc["id"], str) and ID_PATTERN.match(doc["id"])):
        add("id: 1-128 characters of letters, digits, '.', '_' or '-', starting with a letter or digit")
    if "description" in doc and not isinstance(doc["description"], str):
        add("description: must be a string")
    good, bad = doc.get("good"), doc.get("bad")
    for name, side in (("good", good), ("bad", bad)):
        if name in doc and (not isinstance(side, dict) or not side):
            add(f"{name}: must be a non-empty mapping of component name to version")
    if isinstance(good, dict) and isinstance(bad, dict) and good and bad:
        for key in sorted(set(good) ^ set(bad)):
            add(f"{'bad' if key in good else 'good'}.{key}: missing (good and bad need the same components)")
        for key in sorted(set(good) | set(bad)):
            if not (isinstance(key, str) and COMPONENT_PATTERN.match(key)):
                add(f"good.{key}: component names must match {COMPONENT_PATTERN.pattern}")
        for name, side in (("good", good), ("bad", bad)):
            for key, value in side.items():
                if not _finite_json(value):
                    add(f"{name}.{key}: must be a JSON value without NaN or infinity")
        changed = [k for k in good if k in bad and good[k] != bad[k]]
        if set(good) == set(bad) and not changed:
            add("bad: no component differs from good, so there is nothing to diagnose")
        if len(changed) > MAX_CHANGED:
            add(f"bad: {len(changed)} components changed; at most {MAX_CHANGED} are supported")
    _validate_metric(doc.get("metric"), "metric" in doc, add)
    _validate_replay(doc.get("replay"), add)
    _validate_search(doc.get("search"), add)
    _validate_budget(doc.get("budget"), add)
    _validate_adapter(doc, add)
    if "cases" in doc and not (isinstance(doc["cases"], str) and doc["cases"]):
        add("cases: must be a non-empty relative path")
    report = doc.get("report")
    if report is not None:
        if not isinstance(report, dict) or set(report) - {"values"}:
            add("report: only the key 'values' is allowed")
        elif report.get("values", "omit") not in {"redacted", "hashed", "omit"}:
            add("report.values: must be redacted, hashed or omit")
    if "metadata" in doc and not isinstance(doc["metadata"], dict):
        add("metadata: must be a mapping (free-form provenance)")
    return problems


def _validate_metric(metric: Any, present: bool, add: Any) -> None:
    if not present:
        return
    if not isinstance(metric, dict):
        add("metric: must be a mapping with name, direction and regression_threshold")
        return
    for key in sorted(set(metric) - {"name", "direction", "regression_threshold"}):
        add(f"metric.{key}: unknown key")
    if not (isinstance(metric.get("name"), str) and metric["name"].strip()):
        add("metric.name: required non-empty string")
    if metric.get("direction") not in DIRECTIONS:
        add(f"metric.direction: must be one of {', '.join(DIRECTIONS)} (got {metric.get('direction')!r})")
    threshold: Any = metric.get("regression_threshold")
    if not (_number(threshold) and threshold > 0):
        add("metric.regression_threshold: required positive number (the drop that counts as a regression)")


def _validate_replay(replay: Any, add: Any) -> None:
    if replay is None:
        return
    if not isinstance(replay, dict):
        add("replay: must be a mapping")
        return
    allowed = {"repeats", "max_repeats", "confidence", "interval", "noise_scale"}
    for key in sorted(set(replay) - allowed):
        add(f"replay.{key}: unknown key (allowed: {', '.join(sorted(allowed))})")
    interval = replay.get("interval", "student_t")
    if interval not in {"normal", "student_t", "anytime"}:
        add(
            "replay.interval: student_t (default), anytime (diagnosis-level error control) "
            "or normal (historical profile)"
        )
    noise_scale = replay.get("noise_scale")
    if interval == "anytime" and noise_scale is None:
        add("replay.noise_scale: required with interval: anytime (sub-Gaussian scale of one run's noise)")
    elif interval != "anytime" and noise_scale is not None:
        add("replay.noise_scale: applies only to interval: anytime")
    elif noise_scale is not None and not (_number(noise_scale) and noise_scale >= 0):
        add("replay.noise_scale: number of at least 0")
    repeats: Any = replay.get("repeats", 1)
    max_repeats: Any = replay.get("max_repeats", repeats)
    for name, value in (("repeats", repeats), ("max_repeats", max_repeats)):
        if not (_integer(value) and 1 <= value <= 1000):
            add(f"replay.{name}: integer from 1 to 1000")
    if _integer(repeats) and _integer(max_repeats) and max_repeats < repeats:
        add("replay.max_repeats: must be at least replay.repeats")
    confidence = replay.get("confidence", 0.95)
    if not (_number(confidence) and 0.5 <= confidence < 1):
        add("replay.confidence: number from 0.5 up to (not including) 1")


def _validate_search(search: Any, add: Any) -> None:
    if search is None:
        return
    if not isinstance(search, dict):
        add("search: must be a mapping")
        return
    for key in sorted(set(search) - {"strategy", "max_cause_size", "seed"}):
        add(f"search.{key}: unknown key (allowed: strategy, max_cause_size, seed)")
    if search.get("strategy", "adaptive") not in STRATEGY_NAMES:
        add(f"search.strategy: one of {', '.join(STRATEGY_NAMES)}")
    if search.get("max_cause_size", 2) not in (1, 2, 3) or isinstance(search.get("max_cause_size"), bool):
        add("search.max_cause_size: 1, 2 or 3")
    if not (_integer(search.get("seed", 0)) and search.get("seed", 0) >= 0):
        add("search.seed: non-negative integer")


def _validate_budget(budget: Any, add: Any) -> None:
    if budget is None:
        return
    if not isinstance(budget, dict):
        add("budget: must be a mapping")
        return
    for key in sorted(set(budget) - {"max_replays", "audit"}):
        add(f"budget.{key}: unknown key (allowed: max_replays, audit)")
    max_replays: Any = budget.get("max_replays", 16)
    if not (_integer(max_replays) and 2 <= max_replays <= 4096):
        add("budget.max_replays: integer from 2 to 4096 (counts both endpoint replays)")
    audit = budget.get("audit", "extended")
    if not (audit in ("full", "extended") or (_integer(audit) and audit >= 0)):
        add("budget.audit: 'full', 'extended' or a non-negative integer (0 skips the audit)")


def _string_map(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    )


def _validate_adapter(doc: dict[str, Any], add: Any) -> None:
    adapter = doc.get("adapter")
    if adapter is None:
        return
    if not isinstance(adapter, dict):
        add("adapter: must be a mapping with a type")
        return
    kind = adapter.get("type")
    if kind not in ADAPTER_KEYS:
        add(f"adapter.type: one of {', '.join(ADAPTER_KEYS)} (got {kind!r})")
        return
    allowed, required = ADAPTER_KEYS[kind]
    for key in sorted(set(adapter) - allowed):
        add(f"adapter.{key}: unknown key for a {kind} adapter")
    for key in sorted(required - set(adapter)):
        add(f"adapter.{key}: required for a {kind} adapter")
    timeout = adapter.get("timeout_seconds", 1)
    if not (_number(timeout) and timeout > 0):
        add("adapter.timeout_seconds: positive number")
    good: dict[str, Any] = doc["good"] if isinstance(doc.get("good"), dict) else {}
    bad: dict[str, Any] = doc["bad"] if isinstance(doc.get("bad"), dict) else {}
    if kind in {"command", "docker"} and "command" in adapter:
        command = adapter["command"]
        if not (isinstance(command, list) and command and all(isinstance(p, str) and p for p in command)):
            add("adapter.command: non-empty list of non-empty strings (no shell is used)")
    if kind == "command":
        if "env" in adapter and not _string_map(adapter["env"]):
            add("adapter.env: mapping of variable name to string (use ${NAME} to read secrets)")
        if "inherit_env" in adapter and not isinstance(adapter["inherit_env"], bool):
            add("adapter.inherit_env: true or false")
        if "cwd" in adapter and not isinstance(adapter["cwd"], str):
            add("adapter.cwd: relative path string")
        _validate_component_map(adapter.get("interpreters"), "adapter.interpreters", good, bad, add)
    if kind == "python" and not (
        isinstance(adapter.get("callable"), str) and ":" in adapter.get("callable", "")
    ):
        add("adapter.callable: 'module:function'")
    if kind == "http":
        base = adapter.get("base_url")
        if not (
            isinstance(base, str) and (base.startswith(("http://", "https://")) or base.startswith("${"))
        ):
            add("adapter.base_url: http:// or https:// URL (or ${ENV_VAR})")
        mode = adapter.get("mode", "predict")
        if mode not in {"predict", "evaluate"}:
            add("adapter.mode: predict or evaluate")
        if adapter.get("components_via", "header") not in {"header", "body"}:
            add("adapter.components_via: header or body")
        if not (_integer(adapter.get("batch_size", 64)) and adapter.get("batch_size", 64) >= 1):
            add("adapter.batch_size: positive integer")
        if "headers" in adapter and not _string_map(adapter["headers"]):
            add("adapter.headers: mapping of header name to string (use ${NAME} for secrets)")
        if mode == "predict":
            if "cases" not in doc:
                add("cases: required for an http adapter in predict mode")
            metric = doc.get("metric", {}).get("name") if isinstance(doc.get("metric"), dict) else None
            if metric not in HTTP_METRICS:
                add(f"metric.name: predict mode scores locally with one of {', '.join(HTTP_METRICS)}")
    if kind == "docker":
        if ("image" in adapter) == ("images" in adapter):
            add("adapter: give exactly one of image or images")
        if "image" in adapter and not isinstance(adapter["image"], str):
            add("adapter.image: string")
        _validate_component_map(adapter.get("images"), "adapter.images", good, bad, add)


def _validate_component_map(
    value: Any, where: str, good: dict[str, Any], bad: dict[str, Any], add: Any
) -> None:
    if value is None:
        return
    if not (isinstance(value, dict) and set(value) == {"component", "map"} and _string_map(value.get("map"))):
        add(f"{where}: mapping with 'component' and 'map' (version -> path or image)")
        return
    component = value["component"]
    if component not in good:
        add(f"{where}.component: '{component}' is not a component in good/bad")
        return
    for side, state in (("good", good), ("bad", bad)):
        if str(state.get(component)) not in value["map"]:
            add(f"{where}.map: no entry for {side}.{component} = {state.get(component)!r}")
