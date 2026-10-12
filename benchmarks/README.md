# Benchmarks

Protocol, suites and results: **[docs/BENCHMARKS.md](../docs/BENCHMARKS.md)**. Generated tables:
[`results/evaluation/EVALUATION.md`](results/evaluation/EVALUATION.md).

| Path | What |
|---|---|
| `frozen/` | the method freeze: hashes, hyperparameters, behavioral fingerprint (`freeze_method.py`) |
| `incidents/`, `ground_truth.json`, `controls/` | development suite (legacy JSON manifests, frozen) |
| `holdout/` | sealed holdout suite with pre-registration, provenance and seal |
| `higher_order/` | three-way interactions and non-monotone controls (sealed) |
| `results/tables/`, `*/results/tables/` | stored replay observations every strategy is evaluated on |
| `evaluate.py` | all strategies x budgets x audits on every suite, reported separately |
| `configs/frozen_2026_10_08.json`, `reproduce_frozen.py` | explicit historical `full`/`normal` profile, written to a separate output directory |
| `evaluate_safe_default.py`, `results/safe_default/` | secondary release-safety run with current `extended`/`student_t` defaults |
| `prove_ground_truth.py`, `validate_fixtures.py` | prove ground truth by replaying every combination |
| `seal.py` | write and verify suite seals |
| `build_incidents.py` | generator for the development manifests |
| `run_real.py` | the pre-freeze development evaluation (kept for reproducibility of the frozen results) |

Reproduce the original development and holdout method without touching published files:

```bash
python benchmarks/reproduce_frozen.py --output /tmp/regressleuth-frozen-reproduction
```

Run the current product profile separately:

```bash
python benchmarks/evaluate_safe_default.py
```
