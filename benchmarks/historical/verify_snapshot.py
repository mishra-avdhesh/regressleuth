"""Verify the sealed historical pilot against the library source it was evaluated with.

The library keeps changing after the one-time evaluation, so ``harness.py verify`` (which
compares the live source tree with ``FREEZE_MANIFEST.json``) stops passing on the first
library edit. ``frozen_source.tar.gz`` holds the exact frozen files. This script:

1. checks every archived file against the manifest hashes and the source-tree hash;
2. rebuilds a scratch project from the archive plus the sealed benchmark folder and runs
   ``harness.py verify`` there (seal, evidence, source freeze);
3. reruns the evaluation in that scratch project and requires ``rows.json``,
   ``summary.json`` and ``EVALUATION.md`` to equal the published files byte for byte.

    python benchmarks/historical/verify_snapshot.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
ARCHIVE = HERE / "frozen_source.tar.gz"
PUBLISHED = PROJECT / "benchmarks" / "results" / "historical"
COMPARED = ("rows.json", "summary.json", "EVALUATION.md")


def public_seal() -> tuple[dict[str, object], int]:
    """Project the original seal onto files retained in a public checkout.

    The one-time seal accidentally included Ruff cache entries, which Git ignores. The
    original seal remains unchanged and is pinned by the published RUN.json hash.
    """
    seal_bytes = (HERE / "SEAL.json").read_bytes()
    run = json.loads((PUBLISHED / "RUN.json").read_text(encoding="utf-8"))
    if hashlib.sha256(seal_bytes).hexdigest() != run["seal_sha256"]:
        raise ValueError("historical seal differs from the seal pinned by RUN.json")
    seal: dict[str, object] = json.loads(seal_bytes)
    files = seal["files"]
    if not isinstance(files, dict):
        raise ValueError("historical seal has no file mapping")
    retained = {name: digest for name, digest in files.items() if ".ruff_cache" not in Path(name).parts}
    omitted = len(files) - len(retained)
    return {**seal, "files": retained}, omitted


def main() -> int:
    try:
        projected_seal, omitted_cache_files = public_seal()
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    manifest = json.loads((HERE / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    expected: dict[str, str] = manifest["source_file_sha256"]
    canonical = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != manifest["source_tree_sha256"]:
        print("FREEZE_MANIFEST.json does not match its own source-tree hash", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="regressleuth-historical-") as scratch:
        root = Path(scratch)
        with tarfile.open(ARCHIVE, "r:gz") as tar:
            members = tar.getmembers()
            names = sorted(member.name for member in members)
            if names != sorted(expected):
                print("archive does not hold exactly the frozen files", file=sys.stderr)
                return 1
            for member in members:
                target = (root / member.name).resolve()
                if not member.isfile() or not target.is_relative_to(root):
                    print(f"unsafe archived member: {member.name}", file=sys.stderr)
                    return 1
                source = tar.extractfile(member)
                if source is None:
                    print(f"cannot read archived member: {member.name}", file=sys.stderr)
                    return 1
                target.parent.mkdir(parents=True, exist_ok=True)
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        for name, digest in expected.items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
                print(f"archived file differs from the freeze: {name}", file=sys.stderr)
                return 1
        shutil.copytree(
            HERE,
            root / "benchmarks" / "historical",
            ignore=shutil.ignore_patterns("envs", "__pycache__", ".ruff_cache"),
        )
        (root / "benchmarks" / "historical" / "SEAL.json").write_text(
            json.dumps(projected_seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        python = sys.executable
        for script in ("harness.py", "evaluate.py"):
            args = [python, str(root / "benchmarks" / "historical" / script)]
            if script == "harness.py":
                args.append("verify")
            result = subprocess.run(args, cwd=root, capture_output=True, text=True)
            if result.returncode != 0:
                print(result.stdout + result.stderr, file=sys.stderr)
                return 1
        for name in COMPARED:
            rerun = (root / "benchmarks" / "results" / "historical" / name).read_bytes()
            if rerun != (PUBLISHED / name).read_bytes():
                print(f"rerun from the frozen source differs from the published {name}", file=sys.stderr)
                return 1
    print(
        f"frozen source archive matches the freeze ({len(expected)} files); "
        f"public evidence matches the original seal ({omitted_cache_files} generated cache files omitted); "
        f"evaluation reproduced byte for byte ({', '.join(COMPARED)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
