"""Noisy metrics, the monotonicity audit, and environment-interpreter switching."""

from __future__ import annotations

import json
import random
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regressleuth import Incident, investigate
from regressleuth.errors import InvalidIncident


class RobustnessTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        (self.base / "cases.jsonl").write_text('{"label": 1}\n', encoding="utf-8")

    def incident(self, components: tuple[str, ...], **replay: object) -> Incident:
        spec = {
            "command": ["unused"],
            "cases": "cases.jsonl",
            "metric": "accuracy",
            "direction": "higher",
            "regression_threshold": 0.1,
            "timeout_seconds": 5,
            **replay,
        }
        return Incident.from_mapping(
            {
                "id": "robust",
                "good": {name: f"{name}0" for name in components},
                "bad": {name: f"{name}1" for name in components},
                "replay": spec,
            },
            base_dir=self.base,
        )

    def test_noisy_replays_are_repeated_and_judged_with_confidence(self) -> None:
        incident = self.incident(("model", "config", "data"), repeats=4, max_repeats=16)
        calls: list[int] = []

        def replay(state: dict[str, str], _c: Path, _m: str, seed: int = 0) -> float:
            calls.append(seed)
            noise = random.Random(hash((tuple(sorted(state.items())), seed)) & 0xFFFF).gauss(0, 0.02)
            return (0.7 if state["model"] == "model1" else 1.0) + noise

        report = investigate(incident, budget=12, executor=replay)

        # per-comparison Student-t intervals: the cause is found but not verified
        self.assertEqual(report.status, "inferred")
        self.assertEqual(report.diagnosis, ("model",))
        self.assertGreater(report.total_runs, report.experiments_used)
        self.assertTrue(all(e.runs >= 4 for e in report.experiments))
        self.assertIn(3, calls)

        bounded = self.incident(
            ("model", "config", "data"), repeats=4, max_repeats=16, interval="anytime", noise_scale=0.02
        )
        report = investigate(bounded, budget=12, executor=replay)
        self.assertEqual(report.status, "verified")
        self.assertEqual(report.root_cause, ("model",))

    def test_hidden_effect_is_inconclusive_not_guessed(self) -> None:
        incident = self.incident(("model", "config"), repeats=3, max_repeats=6)

        def replay(state: dict[str, str], _c: Path, _m: str, seed: int = 0) -> float:
            drop = 0.12 if state["model"] == "model1" else 0.0
            return 1.0 - drop + random.Random(seed + len(state["config"])).gauss(0, 0.2)

        report = investigate(incident, budget=8, executor=replay)

        self.assertNotIn(report.status, {"verified", "inferred"})
        self.assertIsNone(report.root_cause)

    def test_monotone_violation_is_detected_and_cause_withheld(self) -> None:
        components = ("model", "config", "data", "prep")
        incident = self.incident(components)

        def replay(state: dict[str, str], _c: Path, _m: str) -> float:
            bad = {k for k in components if state[k] == f"{k}1"}
            everything = len(bad) == len(components)
            return 0.6 if ("model" in bad and ("data" not in bad or everything)) else 1.0

        report = investigate(incident, budget=24, executor=replay)

        self.assertEqual(report.status, "assumption_violated")
        self.assertIsNone(report.diagnosis)
        self.assertIsNone(report.root_cause)

    def test_audit_catches_violation_that_search_cannot_see(self) -> None:
        from regressleuth.bench import build_suite, run_one

        suite = {spec.id: spec for spec in build_suite()}
        for strategy in ("adaptive", "ddmin", "greedy"):
            with self.subTest(strategy=strategy):
                report = run_one(suite["control_healed_single_k5"], strategy, 16, seed=0)
                self.assertEqual(report.status, "assumption_violated")
                self.assertIsNone(report.diagnosis)
                self.assertEqual(report.audit["suspected_cause"], ["config"])
                self.assertTrue(report.audit["violations"])

    def test_audit_levels(self) -> None:
        components = ("model", "config", "data", "prep")
        incident = self.incident(components)

        def replay(state: dict[str, str], _c: Path, _m: str) -> float:
            return 0.6 if state["model"] == "model1" else 1.0

        skipped = investigate(incident, budget=24, executor=replay, audit=0)
        partial = investigate(incident, budget=24, executor=replay, audit=1)
        full = investigate(incident, budget=24, executor=replay)

        self.assertEqual(skipped.status, "verified")
        self.assertEqual(skipped.audit["enabled"], False)
        self.assertEqual(partial.status, "inferred")
        self.assertEqual(full.status, "verified")
        self.assertEqual(full.audit["confirmed"], full.audit["required"])
        self.assertLess(skipped.experiments_used, full.experiments_used)
        self.assertEqual(skipped.isolation_replays, full.isolation_replays)

    def test_invalid_audit_and_repeat_settings_are_rejected(self) -> None:
        incident = self.incident(("model", "config"))
        with self.assertRaises(InvalidIncident):
            investigate(incident, executor=lambda *_a: 1.0, audit=-1)
        with self.assertRaises(InvalidIncident):
            self.incident(("model",), repeats=5, max_repeats=2)
        with self.assertRaises(InvalidIncident):
            self.incident(("model",), repeats=0)
        with self.assertRaises(InvalidIncident):
            self.incident(("model",), confidence=1.5)

    def test_environment_component_selects_interpreter(self) -> None:
        for name in ("env_a", "env_b"):
            script = self.base / f"{name}.sh"
            script.write_text(f'#!/bin/sh\nPYTHONPATH= exec "{sys.executable}" "$@"\n', encoding="utf-8")
            script.chmod(script.stat().st_mode | stat.S_IEXEC)
        runner = self.base / "runner.py"
        runner.write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "state = json.loads(Path(sys.argv[1]).read_text())\n"
            "bad = state['components']['environment'] == 'env-b'\n"
            "Path(sys.argv[2]).write_text(json.dumps({'metric': 0.5 if bad else 1.0}))\n",
            encoding="utf-8",
        )
        incident = Incident.from_mapping(
            {
                "id": "env",
                "good": {"environment": "env-a", "model": "m0"},
                "bad": {"environment": "env-b", "model": "m1"},
                "replay": {
                    "command": ["{python}", str(runner), "{state}", "{result}"],
                    "cases": "cases.jsonl",
                    "metric": "accuracy",
                    "direction": "higher",
                    "regression_threshold": 0.1,
                    "timeout_seconds": 20,
                    "interpreters": {
                        "component": "environment",
                        "map": {"env-a": "env_a.sh", "env-b": "env_b.sh"},
                    },
                },
            },
            base_dir=self.base,
        )

        report = investigate(incident, budget=8)

        self.assertEqual(report.status, "verified")
        self.assertEqual(report.root_cause, ("environment",))

    def test_missing_interpreter_is_a_replay_error_without_path_leak(self) -> None:
        incident = Incident.from_mapping(
            {
                "id": "env",
                "good": {"environment": "env-a"},
                "bad": {"environment": "env-b"},
                "replay": {
                    "command": ["{python}", "x"],
                    "cases": "cases.jsonl",
                    "metric": "accuracy",
                    "direction": "higher",
                    "regression_threshold": 0.1,
                    "timeout_seconds": 5,
                    "interpreters": {
                        "component": "environment",
                        "map": {"env-a": "/nonexistent/secret-path/py", "env-b": "missing.sh"},
                    },
                },
            },
            base_dir=self.base,
        )
        report = investigate(incident, budget=4)
        self.assertEqual(report.status, "evaluation_error")
        self.assertNotIn("secret-path", json.dumps(report.to_dict()))


if __name__ == "__main__":
    unittest.main()
