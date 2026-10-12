# Contributing

Bug reports, new incidents with documented provenance, and adapters are the most useful contributions.

```bash
pip install -e ".[demo,dev]"
pytest --cov=regressleuth
ruff check . && ruff format --check . && mypy --strict
python benchmarks/freeze_method.py verify
```

**The method is frozen.** `benchmarks/frozen/` fingerprints the default search. A change that alters
the default behavior must be proposed as a new, opt-in option (and evaluated on a fresh holdout), not
tuned against existing benchmark results.

**Adding an incident.** Start with the [external evidence guide](docs/EXTERNAL_INCIDENTS.md).
Write it in Incident Specification 1.0 with sources in `metadata.provenance`,
then prove its ground truth by replaying every combination (`benchmarks/prove_ground_truth.py SUITE`).
Decide the cause, threshold and decoys *before* running any strategy and record how you chose them.
Do not edit sealed suites (`benchmarks/holdout`, `benchmarks/higher_order`); add a new suite instead.

**Adding an adapter.** Subclass `regressleuth.adapters.Adapter`, return `ReplayOutcome`s with error
kinds instead of raising, keep secrets and absolute paths out of `describe()`, and add contract tests
like `tests/test_adapters.py`.
