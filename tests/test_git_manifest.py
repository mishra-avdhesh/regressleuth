"""Read-only Git artifact manifest intake."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from regressleuth.cli import main


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _command(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(["manifest-diff", *args])
    return code, out.getvalue(), err.getvalue()


class GitManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.manifest = self.repo / "artifacts.json"

    def commit(self, content: str) -> str:
        self.manifest.write_text(content, encoding="utf-8")
        _git(self.repo, "add", "artifacts.json")
        _git(
            self.repo,
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "user.name=Test",
            "commit",
            "-qm",
            "manifest",
        )
        return _git(self.repo, "rev-parse", "HEAD")

    def test_pins_commits_and_hides_values_without_changing_worktree(self) -> None:
        good = self.commit('{"model":"v1","token":"secret-one","cfg":"same"}')
        bad = self.commit('{"model":"v2","token":"secret-two","cfg":"same","new":"n1"}')
        before = _git(self.repo, "status", "--porcelain")
        code, out, err = _command(str(self.repo), good, bad, "artifacts.json")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["good_commit"], good)
        self.assertEqual(data["bad_commit"], bad)
        self.assertEqual(data["changed_components"], ["model", "token"])
        self.assertEqual(data["added_components"], ["new"])
        self.assertEqual(data["unchanged_count"], 1)
        self.assertFalse(data["values_included"])
        self.assertNotIn("secret-one", out)
        self.assertNotIn("v1", out)
        self.assertNotIn(str(self.repo), out)
        self.assertEqual(_git(self.repo, "status", "--porcelain"), before)

        code, out, _ = _command(str(self.repo), good, bad, "artifacts.json", "--include-values")
        self.assertEqual(code, 0)
        values = json.loads(out)
        self.assertEqual(values["good"]["model"], "v1")
        self.assertEqual(values["good"]["token"], "<redacted>")
        self.assertNotIn("secret-one", out)

    def test_rejects_unsafe_paths_duplicate_keys_and_nonfinite_values(self) -> None:
        good = self.commit('{"model":"v1"}')
        bad = self.commit('{"model":"v2","model":"v3"}')
        for path in ("../artifacts.json", "/tmp/artifacts.json", "./artifacts.json"):
            code, _, err = _command(str(self.repo), good, bad, path)
            self.assertEqual(code, 3)
            self.assertIn("safe relative", err)
        code, _, err = _command(str(self.repo), good, bad, "artifacts.json")
        self.assertEqual(code, 3)
        self.assertIn("unique keys", err)
        third = self.commit('{"model":NaN}')
        code, _, err = _command(str(self.repo), good, third, "artifacts.json")
        self.assertEqual(code, 3)
        self.assertIn("NaN or infinity", err)

    def test_missing_ref_or_manifest_is_invalid_input(self) -> None:
        good = self.commit('{"model":"v1"}')
        for bad_ref, path in (("does-not-exist", "artifacts.json"), (good, "missing.json")):
            code, out, err = _command(str(self.repo), good, bad_ref, path)
            self.assertEqual(code, 3)
            self.assertEqual(out, "")
            self.assertIn("could not read", err)
            self.assertNotIn(str(self.repo), err)

    def test_explicit_repo_is_used_even_if_git_dir_is_inherited(self) -> None:
        good = self.commit('{"model":"v1"}')
        bad = self.commit('{"model":"v2"}')
        with mock.patch.dict(os.environ, {"GIT_DIR": str(self.repo / "missing-git-dir")}):
            code, out, err = _command(str(self.repo), good, bad, "artifacts.json")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["changed_components"], ["model"])


if __name__ == "__main__":
    unittest.main()
