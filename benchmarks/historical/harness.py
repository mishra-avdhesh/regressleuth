"""Provenance and integrity checks for the independent historical benchmark.

This module never imports or changes the Regressleuth search implementation.
Run ``python benchmarks/historical/harness.py validate|seal|verify`` from any directory.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
CUTOFF = date(2026, 10, 8)
ALLOWED_STATUSES = {"candidate", "included", "excluded", "disputed"}
REASONS = {
    "no_dated_public_regression",
    "no_good_state",
    "no_bad_state",
    "uninstallable_dependency",
    "unfixed_test",
    "unbounded_changes",
    "infeasible_hybrids",
    "unestablished_cause",
    "private_dependency",
    "duplicate_transition",
    "license_block",
}
REQUIRED_INCLUDED = (
    "known_good_version",
    "known_bad_version",
    "supported_root_cause",
    "root_cause_evidence",
    "fixed_test_cases",
    "failure_metric",
    "threshold",
    "reproduction_environment",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_errors(item: dict[str, Any]) -> list[str]:
    """Validate fields needed at each stage without hiding excluded candidates."""
    errors: list[str] = []
    incident_id = item.get("incident_id")
    if not isinstance(incident_id, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]*", incident_id) is None:
        errors.append("incident_id must be a lowercase slug")
    if not isinstance(item.get("title"), str) or not item["title"].strip():
        errors.append("title is required")
    urls = item.get("source_urls")
    if (
        not isinstance(urls, list)
        or not urls
        or any(
            not isinstance(url, str) or urlparse(url).scheme != "https" or not urlparse(url).netloc
            for url in urls
        )
    ):
        errors.append("source_urls must contain public https URLs")
    try:
        source_date = date.fromisoformat(item["source_date"])
        if source_date >= CUTOFF:
            errors.append("source_date must predate the existing benchmark freeze")
    except (KeyError, TypeError, ValueError):
        errors.append("source_date must be an ISO date")
    if item.get("source_type") not in {
        "github_issue",
        "github_pr",
        "release_note",
        "migration_guide",
        "bug_collection",
    }:
        errors.append("source_type is unsupported")
    if item.get("status") not in ALLOWED_STATUSES:
        errors.append("status is unsupported")
    if item.get("status") == "excluded":
        reasons = item.get("exclusion_reasons")
        if not isinstance(reasons, list) or not reasons or any(r not in REASONS for r in reasons):
            errors.append("excluded candidate needs coded exclusion_reasons")
    if item.get("status") == "included":
        for key in REQUIRED_INCLUDED:
            if item.get(key) in (None, "", []):
                errors.append(f"included candidate missing {key}")
        components = item.get("changed_components")
        if not isinstance(components, list) or not components or len(set(components)) != len(components):
            errors.append("included candidate needs distinct changed_components")
        threshold = item.get("threshold")
        if (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not math.isfinite(threshold)
            or threshold <= 0
        ):
            errors.append("included candidate needs a positive finite threshold")
        if item.get("hybrid_replay_feasibility") != "full":
            errors.append("included candidate needs fully replayable hybrids")
    return errors


def load_candidates(path: Path = ROOT / "CANDIDATES.jsonl") -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    seen: set[str] = set()
    errors: list[str] = []
    for number, row in enumerate(rows, 1):
        errors.extend(f"line {number}: {message}" for message in candidate_errors(row))
        incident_id = row.get("incident_id")
        if incident_id in seen:
            errors.append(f"line {number}: duplicate incident_id {incident_id}")
        seen.add(incident_id)
    if errors:
        raise ValueError("candidate log invalid:\n" + "\n".join(errors))
    return rows


def tracked_files(root: Path = ROOT) -> dict[str, str]:
    """Hash all benchmark definitions and evidence, detecting additions after sealing."""
    required = [
        root / name
        for name in (
            "FREEZE_MANIFEST.json",
            "SELECTION_PROTOCOL.md",
            "ADDENDUM_2026-10-10.md",
            "SEARCH_LOG.md",
            "CANDIDATES.jsonl",
            "harness.py",
            "evaluate.py",
            "setup_envs.py",
            "reproduce.py",
            "ENVIRONMENTS.lock.json",
        )
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"missing benchmark files: {missing}")
    files = (
        required
        + [p for p in (root / "incidents").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        if (root / "incidents").exists()
        else required
    )
    for path in files:
        if path.is_symlink():
            raise ValueError(f"symlink cannot be sealed: {path}")
    return {path.relative_to(root).as_posix(): sha256(path) for path in sorted(files)}


def verify_freeze(path: Path = ROOT / "FREEZE_MANIFEST.json") -> None:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    files: dict[str, str] = freeze["source_file_sha256"]
    changed = [
        name
        for name, expected in files.items()
        if not (PROJECT / name).is_file() or sha256(PROJECT / name) != expected
    ]
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != freeze["source_tree_sha256"] or changed:
        raise ValueError(f"historical source freeze changed: {changed}")


def seal(root: Path = ROOT) -> dict[str, Any]:
    if (root / "SEAL.json").exists():
        # A sealed suite is never re-sealed in place; changes become a new benchmark version.
        raise ValueError(f"{root / 'SEAL.json'} already exists; refusing to replace the seal")
    data = {
        "seal_version": 1,
        "source_tree_sha256": json.loads((root / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))[
            "source_tree_sha256"
        ],
        "files": tracked_files(root),
    }
    (root / "SEAL.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def verify_seal(root: Path = ROOT) -> None:
    sealed = json.loads((root / "SEAL.json").read_text(encoding="utf-8"))
    current = tracked_files(root)
    expected = sealed["files"]
    changed = sorted(name for name in set(current) | set(expected) if current.get(name) != expected.get(name))
    if changed:
        raise ValueError(f"historical seal broken: {changed}")


def validate_evidence(root: Path = ROOT) -> None:
    candidates = load_candidates(root / "CANDIDATES.jsonl")
    for row in candidates:
        if row["status"] != "included":
            continue
        folder = root / "incidents" / row["incident_id"]
        required = (
            "incident.yaml",
            "cases.json",
            "provenance.json",
            "ground_truth.json",
            "replay_table.json",
            "runner.py",
        )
        missing = [name for name in required if not (folder / name).is_file()]
        if missing:
            raise ValueError(f"{row['incident_id']}: missing {missing}")
        truth = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
        if truth.get("incident_id") != row["incident_id"] or not truth.get("established_before_evaluation"):
            raise ValueError(f"{row['incident_id']}: ground truth provenance missing")
        if not isinstance(truth.get("accepted_causes"), list) or not truth["accepted_causes"]:
            raise ValueError(f"{row['incident_id']}: accepted causes missing")
        if not truth.get("evidence_urls"):
            raise ValueError(f"{row['incident_id']}: independent cause evidence missing")
        table = json.loads((folder / "replay_table.json").read_text(encoding="utf-8"))["table"]
        # distribution names are case-insensitive (PEP 503): the ledger's `Pillow` is `pillow`
        components = [re.sub(r"[-_.]+", "-", name).lower() for name in row["changed_components"]]
        expected_masks = {
            "|".join(c for i, c in enumerate(components) if mask & (1 << i))
            for mask in range(1 << len(components))
        }
        if set(table) != expected_masks or any(
            not isinstance(value, list) or not value for value in table.values()
        ):
            raise ValueError(f"{row['incident_id']}: incomplete replay table")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"validate", "seal", "verify"}:
        print("usage: harness.py validate|seal|verify", file=sys.stderr)
        return 2
    mode = argv[1]
    verify_freeze()
    load_candidates()
    if mode == "seal":
        validate_evidence()
        data = seal()
        print(f"sealed {len(data['files'])} historical files")
    elif mode == "verify":
        verify_seal()
        validate_evidence()
        print("historical benchmark seal intact")
    else:
        print("historical provenance and source freeze valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
