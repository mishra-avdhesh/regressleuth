"""Keep a sealed study verifiable after the library moves on.

A study's ``FREEZE_MANIFEST.json`` hashes the library files it was evaluated with, and its
``harness.py verify`` compares them with the live source tree, so the first later library
edit would make that check fail. ``create`` archives exactly the frozen files (refusing
unless they still match the manifest); ``verify`` rebuilds a scratch project from that
archive plus the study folder and runs the study's own ``harness.py verify`` there.

    python benchmarks/snapshot.py create benchmarks/drift
    python benchmarks/snapshot.py verify benchmarks/drift
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ARCHIVE = "frozen_source.tar.gz"


def manifest_files(study: Path) -> dict[str, str]:
    manifest = json.loads((study / "FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    files: dict[str, str] = manifest["files"]
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != manifest["tree_sha256"]:
        raise SystemExit("FREEZE_MANIFEST.json does not match its own tree hash")
    return files


def create(study: Path) -> int:
    files = manifest_files(study)
    if (study / ARCHIVE).exists():
        print(f"{study / ARCHIVE} already exists; refusing to replace it", file=sys.stderr)
        return 3
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(files):
            data = (PROJECT / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != files[name]:
                print(f"{name} no longer matches the freeze; cannot archive", file=sys.stderr)
                return 1
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    with (
        open(study / ARCHIVE, "wb") as handle,
        gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as gz,
    ):
        gz.write(buffer.getvalue())
    print(f"archived {len(files)} frozen files to {study / ARCHIVE}")
    return 0


def verify(study: Path) -> int:
    files = manifest_files(study)
    with tempfile.TemporaryDirectory(prefix="regressleuth-snapshot-") as scratch:
        root = Path(scratch)
        with tarfile.open(study / ARCHIVE, "r:gz") as tar:
            members = tar.getmembers()
            if sorted(member.name for member in members) != sorted(files):
                print("archive does not hold exactly the frozen files", file=sys.stderr)
                return 1
            for member in members:
                target = (root / member.name).resolve()
                if not member.isfile() or not target.is_relative_to(root):
                    print(f"unsafe archived member: {member.name}", file=sys.stderr)
                    return 1
                source = tar.extractfile(member)
                assert source is not None
                target.parent.mkdir(parents=True, exist_ok=True)
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        for name, digest in files.items():
            if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
                print(f"archived file differs from the freeze: {name}", file=sys.stderr)
                return 1
        relative = study.resolve().relative_to(PROJECT)
        shutil.copytree(
            study,
            root / relative,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("work", "__pycache__", ".ruff_cache"),
        )
        result = subprocess.run(
            [sys.executable, str(root / relative / "harness.py"), "verify"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            print(result.stdout + result.stderr, file=sys.stderr)
            return 1
    print(
        f"{relative}: frozen source archive matches the freeze ({len(files)} files); {result.stdout.strip()}"
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"create", "verify"}:
        print(__doc__, file=sys.stderr)
        return 2
    study = Path(argv[2])
    return create(study) if argv[1] == "create" else verify(study)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
