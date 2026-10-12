"""The release archive gate catches leaks without flagging portable examples."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tools.audit_package import inspect_archive


def test_package_audit_rejects_private_files_and_machine_paths(tmp_path: Path) -> None:
    archive = tmp_path / "test.whl"
    with zipfile.ZipFile(archive, "w") as wheel:
        wheel.writestr("pkg/README.md", b"local /home/" + b"person/secret/report.json")
        wheel.writestr("pkg/.agents/AGENTS.md", b"private instructions")
        wheel.writestr("pkg/model.safetensors", b"weights")
    count, findings = inspect_archive(archive)
    assert count == 3
    assert any("local user path" in finding for finding in findings)
    assert any("private path" in finding for finding in findings)
    assert any("weight" in finding for finding in findings)


def test_package_audit_accepts_portable_example_path(tmp_path: Path) -> None:
    archive = tmp_path / "test.whl"
    with zipfile.ZipFile(archive, "w") as wheel:
        wheel.writestr("pkg/README.md", b"python run.py --output /tmp/regressleuth-example")
    assert inspect_archive(archive) == (1, [])
