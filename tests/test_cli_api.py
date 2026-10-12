"""Public API, CLI commands, scaffolding and report renderers."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regressleuth import Incident, diagnose
from regressleuth.cli import main
from regressleuth.reporting import render_html, render_markdown, render_text

GOOD = {"model": "v1", "prep": "p1", "cfg": "c1"}
BAD = {"model": "v2", "prep": "p2", "cfg": "c2"}


def interacting(components: dict[str, str]) -> float:
    return 0.7 if components["model"] == "v2" and components["prep"] == "p2" else 0.95


def legacy_report(good: dict[str, str], bad: dict[str, str], fn: object) -> object:
    """Legacy manifests allow arbitrary component names; used to test escaping."""
    from regressleuth import Incident, investigate

    directory = tempfile.mkdtemp()
    Path(directory, "cases.json").write_text("[]")
    incident = Incident.from_mapping(
        {
            "id": "escape",
            "good": good,
            "bad": bad,
            "replay": {
                "command": ["unused"],
                "cases": "cases.json",
                "metric": "accuracy",
                "direction": "higher",
                "regression_threshold": 0.1,
                "timeout_seconds": 1,
            },
        },
        base_dir=directory,
    )
    return investigate(incident, executor=lambda state, *_a, **_k: fn(state), budget=8)


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ApiTests(unittest.TestCase):
    def test_diagnose_finds_pair_from_a_plain_function(self) -> None:
        report = diagnose(GOOD, BAD, interacting, threshold=0.1)
        self.assertEqual(report.status, "verified")
        self.assertEqual(report.root_cause, ("model", "prep"))
        self.assertIn("model + prep", report.summary())
        self.assertIn("<pre>", report._repr_html_())

    def test_diagnose_supports_noise_via_seed_argument(self) -> None:
        def noisy(components: dict[str, str], seed: int) -> float:
            wobble = ((seed * 37) % 11 - 5) / 400
            return interacting(components) + wobble

        report = diagnose(GOOD, BAD, noisy, threshold=0.1, repeats=4, max_repeats=12)
        # per-comparison intervals bound no diagnosis-level error, so noisy results stop at inferred
        self.assertEqual(report.status, "inferred")
        self.assertIn("noise_scale", report.reason)
        self.assertGreater(report.total_runs, report.experiments_used)
        # the wobble is bounded by 0.0125, hence 0.0125-sub-Gaussian
        bounded = diagnose(GOOD, BAD, noisy, threshold=0.1, repeats=4, max_repeats=12, noise_scale=0.0125)
        self.assertEqual(bounded.status, "verified")
        self.assertEqual(bounded.to_dict()["verification"]["diagnosis_error_bound"], 0.05)

    def test_noise_without_seed_support_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            diagnose(GOOD, BAD, interacting, repeats=3)


class CliTests(unittest.TestCase):
    def test_demo_runs_offline_and_exits_zero(self) -> None:
        code, out, _ = run_cli("demo")
        self.assertEqual(code, 0)
        self.assertIn("normalizer + tokenizer", out)

    def test_init_writes_a_working_template_and_protects_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "inc"
            code, _, _ = run_cli("init", str(target))
            self.assertEqual(code, 0)
            code, out, _ = run_cli("diagnose", str(target / "incident.yaml"))
            self.assertEqual(code, 0)
            self.assertIn("model + preprocessing", out)
            code, _, err = run_cli("init", str(target))
            self.assertEqual(code, 3)
            self.assertIn("not empty", err)

    def test_investigate_formats_and_saved_report_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            saved = Path(directory) / "run.json"
            code, _, _ = run_cli("demo", "--format", "json", "--output", str(saved))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(saved.read_text())["schema_version"], "1.0")
            for fmt, marker in (("html", "<svg"), ("markdown", "## Evidence"), ("text", "Next:")):
                code, out, _ = run_cli("report", str(saved), "--format", fmt)
                self.assertEqual(code, 0)
                self.assertIn(marker, out)
            saved.write_text('{"schema_version": 1}', encoding="utf-8")
            self.assertEqual(run_cli("report", str(saved))[0], 3)

    def test_inspect_describes_the_search_without_running_replays(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_cli("init", directory + "/x")
            code, out, _ = run_cli("inspect", directory + "/x/incident.yaml")
        self.assertEqual(code, 0)
        self.assertIn("Full exhaustive   16 replays", out)
        self.assertIn("No replay was run.", out)

    def test_version_flag(self) -> None:
        with self.assertRaises(SystemExit) as caught, contextlib.redirect_stdout(io.StringIO()):
            main(["--version"])
        self.assertEqual(caught.exception.code, 0)


class ReportTests(unittest.TestCase):
    def test_every_status_renders_in_every_format(self) -> None:
        from regressleuth.bench import build_suite, run_one

        suite = {s.id: s for s in build_suite()}
        wanted = {
            "control_no_regression_k5": "invalid_baseline",
            "control_healed_single_k5": "assumption_violated",
            "control_incompatible_k5": "inferred",
            "single_model_model_k5": "verified",
        }
        for incident_id, status in wanted.items():
            report = run_one(suite[incident_id], "adaptive", 16, seed=0)
            self.assertEqual(report.status, status)
            for render in (render_text, render_markdown, render_html):
                self.assertIn(incident_id, render(report))
        unresolved = run_one(suite["pair_model_preprocessing_k5"], "adaptive", 3, seed=0)
        self.assertEqual(unresolved.status, "unresolved")
        self.assertIn("NO DIAGNOSIS", render_text(unresolved))

    def test_lattice_html_marks_cause_and_escapes_names(self) -> None:
        nasty = '<script>alert("x")</script>'
        report = legacy_report(
            {nasty: "a", "m": "b"}, {nasty: "c", "m": "d"}, lambda s: 0.5 if s[nasty] == "c" else 1.0
        )
        page = render_html(report)
        self.assertNotIn(nasty, page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn('stroke-width="3.5"', page)

    def test_control_characters_are_neutralised_in_terminal_output(self) -> None:
        report = legacy_report(
            {"a\x1b[31m": "1"}, {"a\x1b[31m": "2"}, lambda s: 0.5 if s["a\x1b[31m"] == "2" else 1.0
        )
        self.assertNotIn("\x1b", render_text(report))


if __name__ == "__main__":
    unittest.main()


class CliCommandTests(unittest.TestCase):
    def test_validate_reports_problems_and_accepts_valid_and_legacy_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            run_cli("init", str(base / "inc"))
            self.assertEqual(run_cli("validate", str(base / "inc/incident.yaml"))[0], 0)
            (base / "bad.yaml").write_text("version: '1.0'\nid: x\n", encoding="utf-8")
            code, _, err = run_cli("validate", str(base / "bad.yaml"))
            self.assertEqual(code, 3)
            self.assertIn("good: required", err)
            (base / "cases.json").write_text("[]")
            legacy = {
                "id": "old",
                "good": {"a": 1},
                "bad": {"a": 2},
                "replay": {
                    "command": ["x"],
                    "cases": "cases.json",
                    "metric": "m",
                    "direction": "higher",
                    "regression_threshold": 1,
                    "timeout_seconds": 1,
                },
            }
            (base / "old.json").write_text(json.dumps(legacy))
            code, out, _ = run_cli("validate", str(base / "old.json"))
            self.assertEqual(code, 0)
            self.assertIn("legacy", out)

    def test_schema_command_prints_both_schemas(self) -> None:
        for which in ("incident", "result"):
            code, out, _ = run_cli("schema", which)
            self.assertEqual(code, 0)
            self.assertIn("draft/2020-12", json.loads(out)["$schema"])

    def test_report_rejects_unreadable_or_incomplete_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "r.json"
            self.assertEqual(run_cli("report", str(path))[0], 3)
            path.write_text('{"schema_version": "1.0"}')
            code, _, err = run_cli("report", str(path))
            self.assertEqual(code, 3)
            self.assertIn("incomplete", err)

    def test_diagnose_overrides_and_invalid_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_cli("init", directory + "/inc")
            incident = directory + "/inc/incident.yaml"
            code, out, _ = run_cli(
                "diagnose",
                incident,
                "--strategy",
                "ddmin",
                "--budget",
                "12",
                "--audit",
                "extended",
                "--max-cause-size",
                "3",
                "--format",
                "markdown",
            )
            self.assertEqual(code, 0)
            self.assertIn("## Assumptions", out)
            self.assertEqual(run_cli("diagnose", incident, "--audit", "sometimes")[0], 3)
            self.assertEqual(run_cli("investigate", incident, "--audit", "0")[0], 0)
            self.assertEqual(run_cli("inspect", incident, "--format", "json")[0], 0)
            self.assertEqual(run_cli("init", directory + "/inc", "--force")[0], 0)

    def test_demo_copy_and_html_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, _, _ = run_cli("demo", "--copy", directory + "/demo")
            self.assertEqual(code, 0)
            self.assertTrue((Path(directory) / "demo/incident.yaml").exists())
            self.assertEqual(run_cli("demo", "--format", "html", "--output", directory + "/r.html")[0], 0)
            self.assertIn("<svg", (Path(directory) / "r.html").read_text())

    def test_legacy_command_executor_name(self) -> None:
        from regressleuth.executor import CommandExecutor

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "cases.json").write_text("[]")
            legacy = Incident.from_mapping(
                {
                    "id": "x",
                    "good": {"a": 1},
                    "bad": {"a": 2},
                    "replay": {
                        "command": ["x"],
                        "cases": "cases.json",
                        "metric": "m",
                        "direction": "higher",
                        "regression_threshold": 1,
                        "timeout_seconds": 1,
                    },
                },
                base_dir=directory,
            )
            self.assertEqual(CommandExecutor(legacy).kind, "command")
            spec = Incident.from_spec(
                {
                    "version": "1.0",
                    "id": "p",
                    "good": {"a": 1},
                    "bad": {"a": 2},
                    "metric": {"name": "m", "direction": "higher_is_better", "regression_threshold": 1},
                    "adapter": {"type": "http", "base_url": "http://x", "mode": "evaluate"},
                },
                base_dir=directory,
            )
            with self.assertRaises(TypeError):
                CommandExecutor(spec)

    def test_bench_command_writes_results(self) -> None:
        from regressleuth import bench

        original = bench.run_benchmark

        def small(**_kwargs: object) -> dict:
            return original(budgets=(6, "full"), strategies=("adaptive", "random"), seeds=2)

        with tempfile.TemporaryDirectory() as directory:
            bench.run_benchmark = small  # type: ignore[assignment]
            try:
                code, out, _ = run_cli("bench", "--output-dir", directory, "--seeds", "2")
            finally:
                bench.run_benchmark = original  # type: ignore[assignment]
            self.assertEqual(code, 0)
            self.assertIn("## Controls", out)
            self.assertTrue((Path(directory) / "sleuthbench_synthetic.json").exists())
