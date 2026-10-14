# Regressleuth

**Locate version changes that reproduce an ML regression, including changes that fail only together.**

Regressleuth replays combinations of old and new model, preprocessing, configuration, data, or dependency versions on fixed evaluation cases. It searches within a replay budget, checks a proposed cause, and says when the evidence is insufficient.

**Status:** `0.1.0a1` (alpha). [Try the replay explorer](https://huggingface.co/spaces/avdheshmishra/regressleuth) · [Read the tutorial](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/TUTORIAL.md) · [See the benchmark protocol and results](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/BENCHMARKS.md). The Space displays precomputed reports; run the package locally to diagnose your own incident.

## Try it

From a checkout, with Python 3.10 or newer:

```bash
python -m pip install -e .
regressleuth demo
regressleuth demo --format html --output report.html
```

The bundled incident fails only when two components change together. The report shows the replays, candidate causes, verification settings, and assumptions checked.

## Diagnose your pipeline

Supply good and bad versions plus a function that evaluates each combination on the **same labeled cases**:

```python
from regressleuth import diagnose

good = {"model": "v1", "preprocessing": "p1"}
bad = {"model": "v2", "preprocessing": "p2"}


def run(versions):
    model = load_model(versions["model"])  # your loader
    prep = load_preprocessor(versions["preprocessing"])  # your loader
    return accuracy(model, prep, FIXED_CASES)  # your evaluation


report = diagnose(good, bad, run, threshold=0.03, budget=16)
print(report.summary())
```

The same workflow supports command, HTTP, and Python runners. For a dependency upgrade, install `.[lockfiles]` and create an incident from two lockfiles and a failing test:

```bash
regressleuth init incident --from-lockfiles good.txt bad.txt \
    --project . --test tests/test_upgrade.py::test_regression
regressleuth diagnose incident/incident.yaml
```

See the [worked pandas 2 → 3 lockfile example](https://github.com/mishra-avdhesh/regressleuth/blob/main/examples/lockfile_upgrade/README.md) and [adapter guide](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/ADAPTERS.md) for runnable setups.

## Reading a result

`verified` means **verified under the configured replay model, assumptions, and audit checks**. The proposed combination failed, its tested smaller subsets passed, and the configured audit found no contradiction. It is not unrestricted causal proof. Untested combinations or undeclared changes can invalidate the explanation.

The product default uses the `extended` audit. For repeated noisy metrics, the default interval is Student-t; a noisy result using it can reach at most `inferred`. To allow `verified` with a diagnosis-level error bound, select `interval: anytime` and provide a justified `noise_scale`. Results expose the effective audit mode, interval, confidence, repeat counts, and assumptions checked. [Verification details](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/VERIFICATION.md).

Other outcomes include `inferred` (leading suspect, incomplete checks), `unresolved` (several explanations remain), `inconclusive` (noise obscures the result), and `assumption_violated` (the observed replays contradict the cause model). [Full result schema](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/RESULT_SCHEMA.md).

## Evidence and limits

At a budget of **eight isolation replays** (audit replays are additional):

| Suite | Frozen adaptive | Frozen ddmin | Current default adaptive |
|---|---:|---:|---:|
| Development, 22 author-built incidents | 21/22 correct verified | 16/22 | 21/22 |
| Sealed holdout, 7 author-built incidents | 6/7 | 4/7 | 6/7 |

The current default was evaluated separately on the same stored observations after the audit weakness was found. It caught both known real-model non-monotone controls: **0/60 false verifications**, versus **31/60** with the frozen audit, at higher replay cost. These controls informed the safer default, so this is an in-sample safety check. The holdout is small, and its result depends partly on component-name tie breaks. [Full tables, costs, and protocol](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/BENCHMARKS.md).

An external historical pilot reproduced nine public, single-component regressions without a wrong `verified` result. It does not establish performance on external multi-component incidents; two pre-registered dependency-drift studies found none eligible. Regressleuth builds on existing delta debugging and pipeline diagnosis work; it does not claim a new search algorithm. [Related work](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/RELATED_WORK.md).

The audit cannot cover every combination, and causes larger than the configured `max_cause_size` are outside the search. Replays execute the supplied code without a sandbox; use trusted runners. [More limitations](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/VERIFICATION.md#what-verified-does-not-mean) · [Security](https://github.com/mishra-avdhesh/regressleuth/blob/main/SECURITY.md).

## Reproduce the evaluations

The original frozen profile (`full` audit, `normal` interval) and current product profile (`extended`, Student-t) are kept separate:

```bash
python benchmarks/reproduce_frozen.py --output /tmp/regressleuth-frozen-reproduction
python benchmarks/evaluate_safe_default.py
```

See [benchmarks/README.md](https://github.com/mishra-avdhesh/regressleuth/blob/main/benchmarks/README.md) for prerequisites and outputs. The frozen traces, seals, and published numbers are unchanged.

## Documentation

[Tutorial](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/TUTORIAL.md) · [Incident format](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/INCIDENT_SPEC.md) · [Method](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/METHOD.md) · [Verification](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/VERIFICATION.md) · [Benchmarks](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/BENCHMARKS.md) · [Roadmap](https://github.com/mishra-avdhesh/regressleuth/blob/main/docs/ROADMAP.md)

Apache-2.0 ([license](https://github.com/mishra-avdhesh/regressleuth/blob/main/LICENSE)). Cite as [Avdhesh Mishra, 2026](https://github.com/mishra-avdhesh/regressleuth/blob/main/CITATION.cff).
