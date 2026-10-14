"""Build a runnable incident from two dependency lockfiles.

A dependency upgrade that breaks tests is a natural multi-component incident: every
distribution whose pinned version differs between the known-good and known-bad lockfile
is a component, and a hybrid installs some of them at the bad version and the rest at
the good one. ``write_incident`` turns two lockfiles, a project directory and the failing
tests into ``incident.yaml`` plus ``cases.json``; the replays run through
``python -m regressleuth.lockfile_runner``, which builds one cached virtual environment per
version mix with ``uv``.

Supported lockfiles: requirements-style pins (``pip freeze``, ``uv pip compile``,
``uv export``, ``poetry export``), ``uv.lock`` and ``poetry.lock``. Every format is read
for the target Python version and this platform: requirement markers are evaluated,
``uv.lock`` is walked from its workspace along edges whose markers hold, and
``poetry.lock`` packages are filtered by their markers and Python range.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from .errors import InvalidIncident
from .spec import COMPONENT_PATTERN

_PROJECT_ITSELF = {"-e .", "-e ./", "-e file:.", "--editable .", "--editable ./", "--editable file:."}
_INDEX = re.compile(r"^\s*(?:-i|--index-url|--extra-index-url)(?:\s+|=)(\S+)")
DEFAULT_INDEX = "https://pypi.org/simple"
_NAME = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*==\s*([^\s;#\\]+)")
_HASHES = re.compile(r"(?:\s+--hash(?:=|\s+)\S+)+\s*$")


def normalize(name: str) -> str:
    """PEP 503 name normalization (distribution names are case-insensitive)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _marker_applies(marker: str, python: str) -> bool:
    try:
        from packaging.markers import InvalidMarker, Marker
    except ImportError as exc:  # pragma: no cover - packaging ships with pip and uv
        raise InvalidIncident("environment markers need the 'packaging' distribution") from exc
    environment = {
        "python_version": ".".join(python.split(".")[:2]),
        "python_full_version": python if python.count(".") >= 2 else f"{python}.0",
        "sys_platform": sys.platform,
        "platform_system": {"linux": "Linux", "darwin": "Darwin", "win32": "Windows"}.get(sys.platform, ""),
        "os_name": "nt" if sys.platform == "win32" else "posix",
        "implementation_name": "cpython",
        "platform_python_implementation": "CPython",
    }
    try:
        return bool(Marker(marker).evaluate(environment))
    except InvalidMarker as exc:
        raise InvalidIncident(f"invalid environment marker: {marker!r}") from exc


def parse_requirements(text: str, python: str) -> dict[str, str]:
    """Exact pins from a requirements-style file; markers are evaluated for ``python``."""
    pins: dict[str, str] = {}
    logical = text.replace("\\\n", " ")
    for number, raw in enumerate(logical.splitlines(), 1):
        line = raw.split(" #")[0].strip()
        if not line or line.startswith("#") or line.startswith("--hash"):
            continue
        if line.startswith(
            ("-i ", "--index-url", "--extra-index-url", "--find-links", "-f ", "--trusted-host")
        ):
            continue
        if line.rstrip("/") in {entry.rstrip("/") for entry in _PROJECT_ITSELF}:
            continue  # the project itself (pip-compile writes it); installed separately
        if (
            line.startswith(("-e ", "--editable", "-r ", "-c ", "--requirement", "--constraint"))
            or "@" in line.split(";")[0]
        ):
            raise InvalidIncident(
                f"lockfile line {number}: only exact `name==version` pins are supported (got {line[:60]!r})"
            )
        line = _HASHES.sub("", line)
        requirement, separator, marker = line.partition(";")
        match = _NAME.fullmatch(requirement.strip())
        if not match:
            raise InvalidIncident(f"lockfile line {number}: not an exact `name==version` pin: {line[:60]!r}")
        if separator and not _marker_applies(marker.strip(), python):
            continue
        name, version = normalize(match.group(1)), match.group(3)
        if name in pins and pins[name] != version:
            raise InvalidIncident(
                f"lockfile line {number}: conflicting active pins for {name}: {pins[name]} and {version}"
            )
        pins[name] = version
    return pins


def _toml(text: str) -> dict[str, Any]:
    import importlib

    for module in ("tomllib", "tomli"):  # tomllib from Python 3.11; tomli on 3.10
        try:
            parser = importlib.import_module(module)
        except ModuleNotFoundError:
            continue
        data: dict[str, Any] = parser.loads(text)
        return data
    raise InvalidIncident("reading TOML lockfiles on Python 3.10 needs the 'tomli' distribution")


def _python_admits(spec: str | None, python: str) -> bool:
    """Whether a PEP 440 ``python-versions`` constraint admits ``python`` (unknown syntax: yes)."""
    if not spec or spec.strip() == "*":
        return True
    try:
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
    except ImportError:  # pragma: no cover - packaging ships with pip and uv
        return True
    full = python if python.count(".") >= 2 else f"{python}.0"
    try:
        return SpecifierSet(spec).contains(full, prereleases=True)
    except InvalidSpecifier:  # Poetry's ^ and ~ forms
        return True


def parse_uv_lock(text: str, python: str) -> dict[str, str]:
    """Pins for ``python`` on this platform: walk the dependency graph from the workspace.

    ``uv.lock`` is universal: it may hold several versions of one package for different
    Python versions and platform-only packages. Edges carry markers, so the walk starts at
    the workspace members (all extras and dependency groups) and follows only the edges
    whose markers hold for the target interpreter and this platform.
    """
    packages = _toml(text).get("package", [])
    by_name: dict[str, list[dict[str, Any]]] = {}
    for package in packages:
        by_name.setdefault(normalize(package["name"]), []).append(package)

    def is_member(package: dict[str, Any]) -> bool:
        return any(key in package.get("source", {}) for key in ("virtual", "editable", "directory"))

    def resolve(edge: dict[str, Any]) -> dict[str, Any]:
        options = by_name.get(normalize(edge["name"]), [])
        if "version" in edge:
            options = [option for option in options if str(option.get("version")) == str(edge["version"])]
        if len(options) > 1:
            options = [
                option
                for option in options
                if not option.get("resolution-markers")
                or any(_marker_applies(marker, python) for marker in option["resolution-markers"])
            ]
        if len(options) != 1:
            raise InvalidIncident(f"uv.lock: cannot resolve {edge['name']} for Python {python} unambiguously")
        return options[0]

    roots = [package for package in packages if is_member(package)]
    if not roots:  # no workspace recorded: fall back to package-level resolution markers
        roots_pins = {}
        for name, options in by_name.items():
            chosen = [o for o in options if "registry" in o.get("source", {})]
            chosen = [
                o
                for o in chosen
                if not o.get("resolution-markers")
                or any(_marker_applies(m, python) for m in o["resolution-markers"])
            ]
            if len(chosen) == 1:
                roots_pins[name] = str(chosen[0]["version"])
        return roots_pins
    pins: dict[str, str] = {}
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    stack: list[tuple[dict[str, Any], tuple[str, ...]]] = []
    for root in roots:
        extras = tuple(sorted(root.get("optional-dependencies", {})))
        stack.append((root, extras))
        for group in root.get("dev-dependencies", {}).values():
            for edge in group:
                if "marker" not in edge or _marker_applies(edge["marker"], python):
                    stack.append((resolve(edge), tuple(edge.get("extra", ()))))
    while stack:
        package, extras = stack.pop()
        key = (normalize(package["name"]), str(package.get("version")), extras)
        if key in seen:
            continue
        seen.add(key)
        source = package.get("source", {})
        if "registry" in source:
            pins[key[0]] = str(package["version"])
        elif not is_member(package):
            raise InvalidIncident(
                f"uv.lock: {package['name']} comes from {sorted(source)}; only registry pins are supported"
            )
        edges = list(package.get("dependencies", []))
        for extra in extras:
            edges += package.get("optional-dependencies", {}).get(extra, [])
        for edge in edges:
            if "marker" not in edge or _marker_applies(edge["marker"], python):
                stack.append((resolve(edge), tuple(edge.get("extra", ()))))
    return pins


def parse_poetry_lock(text: str, python: str) -> dict[str, str]:
    """Pins for ``python`` on this platform from each package's markers and Python range.

    Packages that only extras pull in (``optional = true``) are left out, as ``poetry
    install`` does without ``--extras``.
    """
    candidates: dict[str, list[str]] = {}
    for package in _toml(text).get("package", []):
        source = package.get("source") or {}
        if source.get("type") not in (None, "legacy") or "version" not in package or package.get("optional"):
            continue
        markers = package.get("markers")
        if isinstance(markers, dict):
            # a markers table lists only the groups that need one; any other group of the
            # package installs it unconditionally
            groups = package.get("groups") or list(markers)
            applies = any(group not in markers or _marker_applies(markers[group], python) for group in groups)
        else:
            applies = markers is None or _marker_applies(markers, python)
        if applies and _python_admits(package.get("python-versions"), python):
            candidates.setdefault(normalize(package["name"]), []).append(str(package["version"]))
    ambiguous = sorted(name for name, versions in candidates.items() if len(set(versions)) > 1)
    if ambiguous:
        raise InvalidIncident(f"poetry.lock: several versions apply to Python {python}: {ambiguous}")
    return {name: versions[0] for name, versions in candidates.items()}


def read_lockfile(path: Path, python: str) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if path.name == "uv.lock" or (
        text.lstrip().startswith("version = ") and "[[package]]" in text and "source = {" in text
    ):
        pins = parse_uv_lock(text, python)
    elif path.name == "poetry.lock" or ("[[package]]" in text and "content-hash" in text):
        pins = parse_poetry_lock(text, python)
    else:
        pins = parse_requirements(text, python)
    if not pins:
        raise InvalidIncident(f"{path.name}: no exact pins found")
    return pins


def read_indexes(path: Path) -> list[str]:
    """Package indexes other than PyPI that a lockfile installs from (e.g. PyTorch's CPU index)."""
    text = path.read_text(encoding="utf-8")
    urls: set[str] = set()
    if path.name in {"uv.lock", "poetry.lock"} or "[[package]]" in text:
        for package in _toml(text).get("package", []):
            source = package.get("source") or {}
            url = source.get("registry") or (source.get("url") if source.get("type") == "legacy" else None)
            if url:
                urls.add(str(url))
    else:
        for line in text.splitlines():
            match = _INDEX.match(line)
            if match:
                urls.add(match.group(1))
    return sorted(url for url in urls if url.rstrip("/") != DEFAULT_INDEX)


def diff_pins(good: dict[str, str], bad: dict[str, str]) -> dict[str, tuple[str, str]]:
    """Changed distributions as name -> (good value, bad value); ``absent`` marks a missing one."""
    names = sorted(name for name in set(good) | set(bad) if good.get(name) != bad.get(name))
    return {name: (good.get(name, "absent"), bad.get(name, "absent")) for name in names}


def group_components(
    changed: dict[str, tuple[str, str]], groups: list[list[str]]
) -> dict[str, tuple[str, str]]:
    """Merge distributions that change together into one component.

    A removal is often a consequence of another upgrade (pandas 3 dropped its pytz
    requirement), and a mix that keeps old pandas without pytz cannot be installed. A group
    is replayed as a unit; its values list the pins (``pins:a==1,b==2``) on each side.
    """
    merged = dict(changed)
    for raw in groups:
        members = [normalize(name) for name in raw if name.strip()]
        unknown = [name for name in members if name not in merged]
        if len(members) < 2 or unknown:
            raise InvalidIncident(
                f"group {raw}: needs two or more changed distributions (unknown: {unknown})"
            )
        sides = []
        for index in (0, 1):
            pins = [f"{name}=={merged[name][index]}" for name in members if merged[name][index] != "absent"]
            sides.append("pins:" + ",".join(pins))
        for name in members:
            del merged[name]
        merged[members[0]] = (sides[0], sides[1])
    return dict(sorted(merged.items()))


def expand(name: str, value: str) -> list[str]:
    """Pins for one component value (a version, ``absent``, or a group's ``pins:`` list)."""
    if value == "absent":
        return []
    if value.startswith("pins:"):
        return [pin for pin in value[5:].split(",") if pin]
    return [f"{name}=={value}"]


def write_incident(
    good_lock: Path,
    bad_lock: Path,
    *,
    project: Path,
    tests: list[str],
    directory: Path,
    groups: list[list[str]] | None = None,
    python: str = f"{sys.version_info.major}.{sys.version_info.minor}",
    incident_id: str | None = None,
    install_project: str = "editable",
    wheels_only: bool = False,
    pytest_args: tuple[str, ...] = (),
    test_environment: dict[str, str] | None = None,
    timeout_seconds: int = 1800,
    force: bool = False,
) -> dict[str, Any]:
    """Write ``incident.yaml`` and ``cases.json`` for the transition between two lockfiles."""
    if not tests:
        raise InvalidIncident("name at least one failing test (pytest node ID)")
    if install_project not in {"editable", "none"}:
        raise InvalidIncident("install_project must be 'editable' or 'none'")
    good = read_lockfile(good_lock, python)
    bad = read_lockfile(bad_lock, python)
    distributions = diff_pins(good, bad)
    if not distributions:
        raise InvalidIncident("the two lockfiles pin identical versions; there is nothing to diagnose")
    changed = group_components(distributions, groups or [])
    if len(changed) > 12:
        raise InvalidIncident(
            f"{len(changed)} distributions changed; at most 12 are supported. Split the upgrade "
            "(for example by package group) or narrow the transition"
        )
    invalid = [name for name in changed if not COMPONENT_PATTERN.match(name)]
    if invalid:
        raise InvalidIncident(f"distribution names that cannot be component names: {invalid}")
    directory.mkdir(parents=True, exist_ok=True)
    targets = [directory / "incident.yaml", directory / "cases.json"]
    existing = [path.name for path in targets if path.exists()]
    if existing and not force:
        raise InvalidIncident(f"{', '.join(existing)} already exist in {directory}; pass --force to replace")
    shared = sorted(f"{name}=={version}" for name, version in good.items() if name not in distributions)
    try:  # relative to this file, so an incident folder can be moved or shared with its project
        project_path = os.path.relpath(project.resolve(), directory.resolve())
    except ValueError:  # Windows: different drives
        project_path = str(project.resolve())
    cases = {
        "python": python,
        "project": project_path,
        "index_urls": sorted(set(read_indexes(good_lock)) | set(read_indexes(bad_lock))),
        "install_project": install_project,
        "tests": list(tests),
        "pytest_args": list(pytest_args),
        "test_environment": dict(test_environment or {}),
        "wheels_only": wheels_only,
        "shared_pins": shared,
        "test_timeout_seconds": timeout_seconds,
        "environments": ".regressleuth-envs",
    }
    (directory / "cases.json").write_text(
        json.dumps(cases, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    name = incident_id or f"lockfile-{normalize(project.resolve().name) or 'project'}"
    lines = [
        "version: '1.0'",
        f"id: {json.dumps(name)}",
        f"description: {json.dumps(f'Dependency upgrade from {good_lock.name} to {bad_lock.name}')}",
        "good:",
        *[f"  {component}: {json.dumps(values[0])}" for component, values in changed.items()],
        "bad:",
        *[f"  {component}: {json.dumps(values[1])}" for component, values in changed.items()],
        "metric: {name: tests_pass, direction: higher_is_better, regression_threshold: 0.5}",
        "replay: {repeats: 1, max_repeats: 1}",
        "budget: {max_replays: 16, audit: extended}",
        "cases: cases.json",
        "adapter:",
        "  type: command",
        "  command: ['{python}', -m, regressleuth.lockfile_runner, --state, '{state}', --result, '{result}']",
        f"  timeout_seconds: {timeout_seconds + 600}",
        "",
    ]
    (directory / "incident.yaml").write_text("\n".join(lines), encoding="utf-8")
    removed = sorted(name for name, (_, after) in changed.items() if after == "absent")
    return {"changed": changed, "shared": len(shared), "directory": str(directory), "removed": removed}
