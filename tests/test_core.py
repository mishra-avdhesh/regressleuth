"""Behavior tests for counterfactual diagnosis and incident loading."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Keep the stdlib test command usable from a source checkout without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regressleuth import Incident, investigate
from regressleuth.errors import IncompatibleReplay, InvalidIncident, ReplayError
from regressleuth.reporting import render_html


class CoreTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        (self.base / "cases.jsonl").write_text('{"label": 1}\n', encoding="utf-8")

    def incident(
        self,
        good: dict[str, str],
        bad: dict[str, str],
        *,
        command: list[str] | None = None,
        timeout_seconds: float = 2,
    ) -> Incident:
        return Incident.from_mapping(
            {
                "id": "incident-1",
                "good": good,
                "bad": bad,
                "replay": {
                    "command": command or ["unused-with-injected-executor"],
                    "cases": "cases.jsonl",
                    "metric": "accuracy",
                    "direction": "higher",
                    "regression_threshold": 0.1,
                    "timeout_seconds": timeout_seconds,
                },
            },
            base_dir=self.base,
        )

    def test_from_file_resolves_cases_relative_to_incident(self) -> None:
        directory = self.base / "nested"
        directory.mkdir()
        (directory / "cases.jsonl").write_text('{"label": 1}\n', encoding="utf-8")
        payload = {
            "id": "relative-paths",
            "good": {"model": "old"},
            "bad": {"model": "new"},
            "replay": {
                "command": ["{python}", "runner.py", "{state}", "{result}"],
                "cases": "cases.jsonl",
                "metric": "accuracy",
                "direction": "higher",
                "regression_threshold": 0.1,
                "timeout_seconds": 2,
            },
        }
        path = directory / "incident.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        incident = Incident.from_file(path)

        self.assertEqual(incident.replay.cases, directory / "cases.jsonl")
        self.assertEqual(incident.changed_components, ("model",))

    def test_rejects_nonfinite_threshold_and_missing_fixed_cases(self) -> None:
        raw = {
            "id": "invalid",
            "good": {"model": "old"},
            "bad": {"model": "new"},
            "replay": {
                "command": ["unused"],
                "cases": "cases.jsonl",
                "metric": "accuracy",
                "direction": "higher",
                "regression_threshold": float("nan"),
                "timeout_seconds": 2,
            },
        }
        with self.assertRaises(InvalidIncident):
            Incident.from_mapping(raw, base_dir=self.base)

        raw["replay"]["regression_threshold"] = 0.1
        raw["replay"]["cases"] = "missing.jsonl"
        with self.assertRaises(InvalidIncident):
            Incident.from_mapping(raw, base_dir=self.base)

    def test_invalid_utf8_incident_file_raises_invalid_incident(self) -> None:
        path = self.base / "invalid.json"
        path.write_bytes(b"\xff\xfe\x00")

        with self.assertRaises(InvalidIncident):
            Incident.from_file(path)

    def test_input_and_selected_state_mutation_cannot_change_incident(self) -> None:
        good = {"config": {"threshold": 0.5}, "model": "old"}
        bad = {"config": {"threshold": 0.9}, "model": "new"}
        raw = {
            "id": "mutable-input",
            "good": good,
            "bad": bad,
            "replay": {
                "command": ["unused"],
                "cases": "cases.jsonl",
                "metric": "accuracy",
                "direction": "higher",
                "regression_threshold": 0.1,
                "timeout_seconds": 2,
            },
        }
        incident = Incident.from_mapping(raw, base_dir=self.base)

        good["config"]["threshold"] = 99
        bad["config"]["threshold"] = 99
        bad["model"] = "replaced"
        selected = incident.selected_state(frozenset({"config"}))
        selected["config"]["threshold"] = -1

        self.assertEqual(incident.good["config"], {"threshold": 0.5})
        self.assertEqual(incident.bad["config"], {"threshold": 0.9})
        self.assertEqual(incident.bad["model"], "new")
        self.assertEqual(
            incident.selected_state(frozenset({"config"})),
            {"config": {"threshold": 0.9}, "model": "old"},
        )

    def test_finds_single_component_without_attributing_other_changes(self) -> None:
        good = {"model": "m0", "preprocessing": "p0", "config": "c0", "stable": "same"}
        bad = {"model": "m1", "preprocessing": "p1", "config": "c1", "stable": "same"}
        incident = self.incident(good, bad)

        def replay(state: dict[str, str], cases: Path, metric: str) -> float:
            self.assertEqual(cases, self.base / "cases.jsonl")
            self.assertEqual(metric, "accuracy")
            return 0.7 if state["model"] == "m1" else 1.0

        report = investigate(incident, budget=12, executor=replay)

        self.assertEqual(report.status, "verified")
        self.assertEqual(report.root_cause, ("model",))
        self.assertLessEqual(report.isolation_replays, 12)
        self.assertEqual(report.experiments[0].changed, ())
        self.assertEqual(report.experiments[1].changed, incident.changed_components)

    def test_finds_pairwise_interaction_when_single_changes_pass(self) -> None:
        good = {"model": "m0", "preprocessing": "p0", "config": "c0", "data": "d0"}
        bad = {"model": "m1", "preprocessing": "p1", "config": "c1", "data": "d1"}
        incident = self.incident(good, bad)

        def replay(state: dict[str, str], _cases: Path, _metric: str) -> float:
            return 0.65 if state["model"] == "m1" and state["preprocessing"] == "p1" else 1.0

        report = investigate(incident, budget=24, executor=replay)

        self.assertEqual(report.status, "verified")
        self.assertEqual(report.root_cause, ("model", "preprocessing"))
        evidence = {experiment.changed: experiment.outcome for experiment in report.experiments}
        self.assertEqual(evidence[("model",)], "pass")
        self.assertEqual(evidence[("preprocessing",)], "pass")

    def test_nonregressing_bad_baseline_blocks_attribution(self) -> None:
        incident = self.incident({"model": "old"}, {"model": "new"})
        seen: list[dict[str, str]] = []

        def replay(state: dict[str, str], _cases: Path, _metric: str) -> float:
            seen.append(state)
            return 1.0 if state["model"] == "old" else 0.98

        report = investigate(incident, budget=8, executor=replay)

        self.assertEqual(report.status, "invalid_baseline")
        self.assertIsNone(report.root_cause)
        self.assertEqual(len(seen), 2)
        self.assertEqual(report.experiments_used, 2)

    def test_budget_includes_both_baselines_and_never_overruns(self) -> None:
        incident = self.incident({"model": "m0", "config": "c0"}, {"model": "m1", "config": "c1"})
        with self.assertRaises(InvalidIncident):
            investigate(incident, budget=1, executor=lambda *_args: 1.0)
        for budget in (2, 3):
            with self.subTest(budget=budget):
                calls: list[dict[str, str]] = []

                def replay(state: dict[str, str], _cases: Path, _metric: str, calls: list = calls) -> float:
                    calls.append(state)
                    return 0.7 if state["model"] == "m1" else 1.0

                report = investigate(incident, budget=budget, executor=replay)
                self.assertEqual(len(calls), report.experiments_used)
                self.assertLessEqual(report.isolation_replays, budget)
                self.assertIsNone(report.root_cause)
                self.assertEqual(report.experiments[0].role, "baseline")
                self.assertEqual(report.experiments[1].role, "baseline")

    def test_hybrid_incompatibility_and_runtime_errors_are_distinct(self) -> None:
        incident = self.incident(
            {"model": "m0", "preprocessing": "p0"},
            {"model": "m1", "preprocessing": "p1"},
        )
        for error_type, outcome in (
            (IncompatibleReplay, "incompatible"),
            (ReplayError, "error"),
        ):
            with self.subTest(outcome=outcome):

                def replay(
                    state: dict[str, str], _cases: Path, _metric: str, error_type: type = error_type
                ) -> float:
                    changed = sum(state[key] == incident.bad[key] for key in incident.changed_components)
                    if changed == 1:
                        raise error_type("private process detail")
                    return 0.7 if changed == 2 else 1.0

                report = investigate(incident, budget=8, executor=replay)
                self.assertIn(outcome, [experiment.outcome for experiment in report.experiments])
                self.assertNotEqual(report.status, "verified")
                self.assertIsNone(report.root_cause)

    def test_report_omits_component_values_and_replay_exception_text(self) -> None:
        secret = "sk-secret-value-never-in-report"
        incident = self.incident(
            {"model": secret, "preprocessing": "p0"},
            {"model": "m1", "preprocessing": "p1"},
        )

        def replay(state: dict[str, str], _cases: Path, _metric: str) -> float:
            if state["model"] == "m1" and state["preprocessing"] == "p0":
                raise ReplayError("stderr contained " + secret)
            return 0.7 if state["model"] == "m1" and state["preprocessing"] == "p1" else 1.0

        report = investigate(incident, budget=8, executor=replay)
        serialized = json.dumps(report.to_dict())

        self.assertIn("error", [experiment.outcome for experiment in report.experiments])
        self.assertNotIn(secret, serialized)
        self.assertNotIn("stderr contained", serialized)

    def test_default_command_executor_reads_state_and_result_files(self) -> None:
        script = self.base / "runner.py"
        script.write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            "state = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
            "assert state['cases'] == str(Path('cases.jsonl').resolve())\n"
            "assert state['metric'] == 'accuracy'\n"
            "score = 0.7 if state['components']['model'] == 'm1' else 1.0\n"
            "Path(sys.argv[2]).write_text(json.dumps({'metric': score}), encoding='utf-8')\n",
            encoding="utf-8",
        )
        incident = self.incident(
            {"model": "m0", "config": "c0"},
            {"model": "m1", "config": "c1"},
            command=["{python}", str(script), "{state}", "{result}"],
        )

        report = investigate(incident, budget=8)

        self.assertEqual(report.status, "verified")
        self.assertEqual(report.root_cause, ("model",))

    def test_command_timeout_is_reported_without_process_output(self) -> None:
        script = self.base / "slow_runner.py"
        script.write_text(
            "import sys, time\nprint('private subprocess output', file=sys.stderr)\ntime.sleep(0.5)\n",
            encoding="utf-8",
        )
        incident = self.incident(
            {"model": "m0"},
            {"model": "m1"},
            command=["{python}", str(script), "{state}", "{result}"],
            timeout_seconds=0.05,
        )

        report = investigate(incident, budget=8)

        self.assertEqual(report.status, "evaluation_error")
        self.assertEqual(report.experiments_used, 1)
        self.assertEqual(report.experiments[0].outcome, "error")
        self.assertNotIn("private subprocess output", json.dumps(report.to_dict()))

    def test_html_report_escapes_user_supplied_component_names(self) -> None:
        component = '<img src=x onerror="alert(1)">'
        incident = self.incident({component: "old"}, {component: "new"})

        def replay(state: dict[str, str], _cases: Path, _metric: str) -> float:
            return 1.0 if state[component] == "old" else 0.7

        report = investigate(incident, budget=2, executor=replay)
        html = render_html(report)

        self.assertNotIn(component, html)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", html)


if __name__ == "__main__":
    unittest.main()
