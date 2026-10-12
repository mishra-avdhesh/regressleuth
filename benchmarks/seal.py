"""Seal a benchmark suite: record SHA-256 of every file that defines it.

    python benchmarks/seal.py write benchmarks/holdout
    python benchmarks/seal.py verify benchmarks/holdout
    python benchmarks/seal.py verify benchmarks/holdout --definitions-only   # fresh clone, no data/

Evaluation scripts call ``verify`` first and refuse to run on a changed suite. The seal
also records the frozen-method tree hash, tying the results to the frozen method.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PATTERNS = (
    "PREREGISTRATION.md",
    "ground_truth.json",
    "incidents/*.yaml",
    "controls/*.yaml",
    "controls/*.json",
    "runners/*.py",
    "prepare.py",
    "setup_envs.py",
    "results/tables/*.json",
    "results/ground_truth_proofs.json",
    "data/**/*.json",
)


def digest(suite: Path) -> dict[str, str]:
    files = sorted({p for pattern in PATTERNS for p in suite.glob(pattern) if p.is_file()})
    return {str(p.relative_to(suite)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main(mode: str, suite: Path, definitions_only: bool = False) -> int:
    seal_path = suite / "SEAL.json"
    frozen = json.loads((Path(__file__).resolve().parent / "frozen" / "frozen_method.json").read_text())
    if mode == "write":
        seal = {
            "sealed_on": "2026-10-08",
            "frozen_method_tree_sha256": frozen["source"]["tree_sha256"],
            "files": digest(suite),
        }
        seal_path.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"sealed {len(seal['files'])} files in {suite.name}")
        return 0
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    current = digest(suite)
    sealed = seal["files"]
    if definitions_only:  # generated data is not committed; check everything else
        sealed = {k: v for k, v in sealed.items() if not k.startswith("data/")}
        current = {k: v for k, v in current.items() if not k.startswith("data/")}
    changed = sorted(k for k in set(sealed) | set(current) if sealed.get(k) != current.get(k))
    if changed:
        print(f"SEAL BROKEN in {suite.name}: {changed[:8]}")
        return 1
    print(f"seal intact: {len(current)} files in {suite.name} unchanged since sealing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], Path(sys.argv[2]).resolve(), "--definitions-only" in sys.argv))
