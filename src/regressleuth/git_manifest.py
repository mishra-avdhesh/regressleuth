"""Read-only comparison of versioned component manifests stored in Git."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import InvalidIncident
from .redact import redact_state
from .spec import COMPONENT_PATTERN

MAX_MANIFEST_BYTES = 1_048_576
COMMIT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def _git(repo: Path, *args: str) -> bytes:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(name, None)
    try:
        process = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            timeout=10,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvalidIncident("Git could not read the requested commit or manifest") from exc
    if process.returncode:
        raise InvalidIncident("Git could not read the requested commit or manifest")
    return process.stdout


def _commit(repo: Path, ref: str) -> str:
    if not ref or ref.startswith("-") or any(ord(char) < 32 for char in ref):
        raise InvalidIncident("Git refs must be nonempty and contain no control characters")
    commit = _git(repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    value = commit.decode("ascii", errors="replace").strip()
    if not COMMIT_ID.fullmatch(value):
        raise InvalidIncident("Git did not return a valid commit ID")
    return value


def _manifest_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or value.startswith("-")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise InvalidIncident("manifest path must be a safe relative POSIX path in Git")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate JSON key")
        output[key] = value
    return output


def _read_manifest(repo: Path, commit: str, path: str) -> tuple[dict[str, Any], str]:
    spec = f"{commit}:{path}"
    try:
        size = int(_git(repo, "cat-file", "-s", spec).strip())
    except ValueError as exc:
        raise InvalidIncident("Git returned an invalid manifest size") from exc
    if size > MAX_MANIFEST_BYTES:
        raise InvalidIncident("manifest exceeds the 1 MiB limit")
    raw = _git(repo, "cat-file", "blob", spec)
    if len(raw) != size:
        raise InvalidIncident("manifest changed while reading Git objects")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, ValueError) as exc:
        raise InvalidIncident("manifest must be UTF-8 JSON with unique keys") from exc
    if not isinstance(value, dict) or not value:
        raise InvalidIncident("manifest must be a nonempty JSON object of components")
    if any(not COMPONENT_PATTERN.fullmatch(key) for key in value):
        raise InvalidIncident("manifest contains an invalid component name")
    try:
        json.dumps(value, allow_nan=False)
    except ValueError as exc:
        raise InvalidIncident("manifest contains NaN or infinity") from exc
    return value, hashlib.sha256(raw).hexdigest()


def compare_git_manifests(
    repo: str | Path,
    good_ref: str,
    bad_ref: str,
    manifest_path: str,
    *,
    include_values: bool = False,
) -> dict[str, Any]:
    """Compare JSON component maps at two commits without modifying the repository."""
    repository = Path(repo)
    if not repository.is_dir():
        raise InvalidIncident("repository directory does not exist")
    path = _manifest_path(manifest_path)
    good_commit, bad_commit = _commit(repository, good_ref), _commit(repository, bad_ref)
    good, good_sha256 = _read_manifest(repository, good_commit, path)
    bad, bad_sha256 = _read_manifest(repository, bad_commit, path)
    common = good.keys() & bad.keys()
    changed = sorted(key for key in common if good[key] != bad[key])
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "manifest_path": path,
        "good_commit": good_commit,
        "bad_commit": bad_commit,
        "good_manifest_sha256": good_sha256,
        "bad_manifest_sha256": bad_sha256,
        "changed_components": changed,
        "added_components": sorted(bad.keys() - good.keys()),
        "removed_components": sorted(good.keys() - bad.keys()),
        "unchanged_count": len(common) - len(changed),
        "values_included": include_values,
    }
    if include_values:
        result["good"] = redact_state(good, "redacted")
        result["bad"] = redact_state(bad, "redacted")
    return result
