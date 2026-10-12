"""Strategy and SleuthBench-synthetic behavior tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regressleuth.bench import build_suite, run_benchmark, run_one
from regressleuth.strategies import STRATEGIES


class StrategyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = {spec.id: spec for spec in build_suite()}

    def test_every_strategy_finds_single_and_pair_causes_with_ample_budget(self) -> None:
        for strategy in STRATEGIES:
            for incident_id in ("single_model_model_k5", "pair_model_preprocessing_k5"):
                spec = self.suite[incident_id]
                if strategy == "one_factor" and spec.kind == "pair":
                    continue
                with self.subTest(strategy=strategy, incident=incident_id):
                    report = run_one(spec, strategy, 64, seed=3)
                    self.assertEqual(report.status, "verified")
                    self.assertEqual(frozenset(report.diagnosis or ()), spec.cause)

    def test_one_factor_cannot_resolve_pair_interactions(self) -> None:
        report = run_one(self.suite["pair_model_preprocessing_k5"], "one_factor", 64, seed=0)
        self.assertNotEqual(report.status, "verified")
        self.assertGreater(len(report.candidates), 1)

    def test_budget_is_never_exceeded_and_masks_are_never_repeated(self) -> None:
        for strategy in STRATEGIES:
            for spec in self.suite.values():
                with self.subTest(strategy=strategy, incident=spec.id):
                    report = run_one(spec, strategy, 7, seed=1)
                    masks = [e.changed for e in report.experiments]
                    self.assertLessEqual(report.isolation_replays, 7)
                    self.assertEqual(len(masks), len(set(masks)))

    def test_exhaustive_enumerates_every_mask_when_budget_allows(self) -> None:
        spec = self.suite["single_model_model_k5"]
        report = run_one(spec, "exhaustive", 64, seed=0)
        self.assertEqual(report.experiments_used, 2**5)

    def test_random_is_reproducible_per_seed(self) -> None:
        spec = self.suite["pair_config_calibration_k6"]
        first = [e.changed for e in run_one(spec, "random", 16, seed=5).experiments]
        again = [e.changed for e in run_one(spec, "random", 16, seed=5).experiments]
        other = [e.changed for e in run_one(spec, "random", 16, seed=6).experiments]
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)

    def test_three_way_and_no_regression_controls_never_verify(self) -> None:
        for strategy in STRATEGIES:
            for incident_id in ("control_three_way_k6", "control_no_regression_k5"):
                with self.subTest(strategy=strategy, incident=incident_id):
                    report = run_one(self.suite[incident_id], strategy, 64, seed=0)
                    self.assertNotEqual(report.status, "verified")

    def test_suite_meets_declared_release_shape(self) -> None:
        valid = [s for s in self.suite.values() if s.valid]
        self.assertGreaterEqual(len(valid), 20)
        self.assertGreaterEqual(sum(s.kind == "pair" for s in valid), 5)
        self.assertGreaterEqual(len({s.category for s in valid} - {"interaction"}), 4)

    def test_benchmark_is_deterministic(self) -> None:
        first = run_benchmark(budgets=(6, 12), strategies=("adaptive", "random"), seeds=3)
        second = run_benchmark(budgets=(6, 12), strategies=("adaptive", "random"), seeds=3)
        self.assertEqual(first["summary"], second["summary"])


if __name__ == "__main__":
    unittest.main()
