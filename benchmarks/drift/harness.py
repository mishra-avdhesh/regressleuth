"""Integrity checks for the dependency-drift suite: ledger, method freeze, evidence, seal.

    python benchmarks/drift/harness.py validate|seal|verify

This module never imports or changes the Regressleuth search implementation.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
STATUSES = {"candidate", "excluded", "disputed", "included"}
REASONS = {
    "no_dated_public_report",
    "outside_population",
    "not_dependency_drift",
    "no_fixed_test",
    "unresolvable_requirements",
    "build_infeasible",
    "download_too_large",
    "search_space_above_cap",
    "duplicate_transition",
}
REPLAY_FIELDS = (
    "distribution",
    "fixed_commit",
    "d_good",
    "d_bad",
    "python",
    "requirements",
    "test_node_ids",
    "blamed",
)
EVIDENCE = (
    "incident.yaml",
    "cases.json",
    "good.txt",
    "bad.txt",
    "source.json",
    "provenance.json",
    "ground_truth.json",
    "replay_table.json",
)
TRACKED = (
    "SELECTION_PROTOCOL.md",
    "ADDENDUM_2026-10-11.md",
    "ADDENDUM_2026-10-11b.md",
    "FREEZE_MANIFEST.json",
    "FREEZE_MANIFEST.v0.json",
    "SEARCH_LOG.md",
    "REPLAY_LOG.md",
    "CANDIDATES.jsonl",
    "drift.py",
    "runner.py",
    "harness.py",
    "evaluate.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_errors(row: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("incident_id", "title", "source_urls", "source_date", "project", "status"):
        if not row.get(key):
            errors.append(f"{key} is required")
    if row.get("status") not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")
    reasons = row.get("exclusion_reasons", [])
    if row.get("status") == "excluded" and (not reasons or not set(reasons) <= REASONS):
        errors.append("excluded candidate needs coded exclusion_reasons")
    if row.get("status") != "excluded" and reasons:
        errors.append("only excluded candidates carry exclusion_reasons")
    if row.get("status") in {"included", "disputed"}:
        errors += [f"{key} is required for a replayed candidate" for key in REPLAY_FIELDS if not row.get(key)]
    return errors


def load_candidates(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or ROOT / "CANDIDATES.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row.get("incident_id") for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate incident_id in the ledger")
    problems = {row.get("incident_id"): candidate_errors(row) for row in rows}
    problems = {key: value for key, value in problems.items() if value}
    if problems:
        raise ValueError(f"invalid candidates: {problems}")
    return rows


def verify_freeze(root: Path = ROOT) -> None:
    manifest = json.loads((root / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    files: dict[str, str] = manifest["files"]
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    changed = [
        name
        for name, digest in files.items()
        if not (PROJECT / name).is_file() or sha256(PROJECT / name) != digest
    ]
    if hashlib.sha256(canonical).hexdigest() != manifest["tree_sha256"] or changed:
        raise ValueError(f"drift method freeze changed: {changed}")


def tracked_files(root: Path = ROOT) -> dict[str, str]:
    required = [root / name for name in TRACKED]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError(f"missing benchmark files: {missing}")
    incidents = root / "incidents"
    files = required + (
        [
            p
            for p in incidents.rglob("*")
            if p.is_file() and not {"__pycache__", ".ruff_cache"}.intersection(p.parts)
        ]
        if incidents.exists()
        else []
    )
    return {str(path.relative_to(root)): sha256(path) for path in sorted(files)}


def validate_evidence(root: Path = ROOT) -> None:
    for row in load_candidates(root / "CANDIDATES.jsonl"):
        if row["status"] != "included":
            continue
        folder = root / "incidents" / row["incident_id"]
        missing = [name for name in EVIDENCE if not (folder / name).is_file()]
        if missing:
            raise ValueError(f"{row['incident_id']}: missing {missing}")
        truth = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
        if not truth.get("established_before_evaluation") or not truth.get("accepted_causes"):
            raise ValueError(f"{row['incident_id']}: ground truth missing")
        replay = json.loads((folder / "replay_table.json").read_text(encoding="utf-8"))
        components = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))[
            "changed_components"
        ]
        if not replay.get("complete") or len(replay["table"]) != 2 ** len(components):
            raise ValueError(f"{row['incident_id']}: incomplete replay table")


def seal(root: Path = ROOT) -> dict[str, Any]:
    if (root / "SEAL.json").exists():
        raise ValueError(f"{root / 'SEAL.json'} already exists; refusing to replace the seal")
    manifest = json.loads((root / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    data = {"seal_version": 1, "method_tree_sha256": manifest["tree_sha256"], "files": tracked_files(root)}
    (root / "SEAL.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def verify_seal(root: Path = ROOT) -> None:
    sealed = json.loads((root / "SEAL.json").read_text(encoding="utf-8"))["files"]
    current = tracked_files(root)
    changed = sorted(name for name in set(current) | set(sealed) if current.get(name) != sealed.get(name))
    if changed:
        raise ValueError(f"drift seal broken: {changed}")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"validate", "seal", "verify"}:
        print("usage: harness.py validate|seal|verify", file=sys.stderr)
        return 2
    verify_freeze()
    load_candidates()
    if argv[1] == "seal":
        validate_evidence()
        print(f"sealed {len(seal()['files'])} drift files")
    elif argv[1] == "verify":
        verify_seal()
        validate_evidence()
        print("drift benchmark seal intact")
    else:
        print("drift ledger and method freeze valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
