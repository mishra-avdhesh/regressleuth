# Regressleuth

**Find which of several changed versions broke your ML pipeline or test suite: verified, or an explicit "I can't tell".**

A deploy changed the model, the preprocessing, a config value, the data export and a library version, and accuracy dropped. A dependency update bumped eight packages, and a test now fails. Which change did it, or which *pair* of changes? Regressleuth replays mixes of the old and new versions on your fixed cases. It picks each next replay to rule out as many explanations as possible and reports the smallest set of changes that reproduces the regression. Every answer comes with the evidence, the assumptions it checked, and an explicit refusal when the evidence does not support a single answer.

Budgeted counterfactual search over versioned components, including interaction failures, with explicit verification and assumption-violation handling.

> **Status: `0.1.0a1` (alpha).** Read [What it does not claim](#what-it-does-not-claim) and [Limitations](#limitations) before relying on it. A short technical overview: [project case study](docs/CASE_STUDY.md).

## Why one change at a time is not enough

| model | feature assembler | result |
|---|---|---|
| old | old | pass |
| new | old | pass |
| old | new | pass |
| new | new | **fail** |

With `k` changed components there are `2^k` combinations. Regressleuth searches them adaptively within a replay budget. It then confirms the answer (the cause's own combination fails and every smaller subset passes) and audits the assumption behind the search before calling anything `verified`.

## Quickstart

```bash
pip install -e .            # from a checkout; Python 3.10+ (`pip install regressleuth` once released)
regressleuth demo           # offline, standard library only
```

```text
Status: VERIFIED
CAUSE: normalizer + tokenizer
Replays: isolation 7/16 + audit 6; full exhaustive search = 16
Verification: audit extended; interval student_t (not applied: deterministic); confidence 0.95; repeats 1/1
```

`regressleuth demo --format html --output report.html` shows both states, every combination tried, how candidate causes were eliminated, the verification settings and the assumption checks. A free, static [replay explorer](space_static) with precomputed reports can be hosted on Hugging Face Static Spaces or GitHub Pages; the live [Gradio app](space) runs locally.

## Use case 1: a dependency upgrade broke the tests

Give Regressleuth the two lockfiles and the failing test. Every distribution whose pin differs becomes a component. Each replay installs one mix of old and new versions into a cached virtual environment (with [uv](https://docs.astral.sh/uv/)) and runs the test.

```bash
pip install -e ".[lockfiles]"
regressleuth init incident --from-lockfiles good.txt bad.txt \
    --project . --test tests/test_features.py::test_clip_and_round --group pandas,pytz,tzdata
regressleuth diagnose incident/incident.yaml
```

- **Lockfile formats:** requirements-style pins (`pip freeze`, `uv pip compile`, `uv export`, `poetry export`), `uv.lock` or `poetry.lock`. Each is read for the target Python and platform, including custom package indexes such as PyTorch's CPU index.
- **Input validation:** malformed requirement lines and conflicting pins active on the same target Python are rejected before any environment is built.
- **Uninstallable mixes:** a mix that cannot be installed, or that `uv pip check` rejects, is reported as incompatible. It never counts as a pass.
- **Integrity:** installed files are checked against their wheels' recorded hashes.
- **Grouping:** `--group` replays an upgrade together with the dependencies it dropped.

[Worked example with real wheels](examples/lockfile_upgrade): pandas 2.3.3 → 3.0.0 among five changed distributions comes out **`verified`: pandas** after 8 replays.

## Use case 2: a model or pipeline regressed

Write a function (or a command, or point at an HTTP service) that builds the pipeline from a dict of component versions and returns the metric on fixed cases:

```python
from regressleuth import diagnose

good = {"model": "v4", "preprocessing": "a1b2c3", "config": "old", "data": "2026-09"}
bad = {"model": "v5", "preprocessing": "d4e5f6", "config": "new", "data": "2026-10"}


def run(components):  # each value is the good OR the bad version
    pipeline = build(components)  # your code: load the versions named here
    return accuracy(pipeline, FIXED_CASES)  # same labeled cases every call


report = diagnose(good, bad, run, threshold=0.03, budget=16, audit="extended")
print(report.status, report.root_cause)  # in Jupyter, `report` renders itself
```

- **Noisy metric:** let `run` accept a `seed`, and pass `repeats=3, max_repeats=24, noise_scale=...`. `regressleuth noise-scale incident.yaml` suggests a safe `noise_scale`.
- **Unbuildable mix:** raise `regressleuth.errors.IncompatibleReplay`.
- **Real service:** [`examples/http_service`](examples/http_service) diagnoses a regressed scikit-learn scoring service purely over HTTP. Recorded result: `feature_assembler + model` verified after 8 isolation and 13 audit replays, in 1.6 s.

## CLI

```bash
regressleuth init my_incident                      # runnable template: incident.yaml + runner.py + cases.json
regressleuth init incident --from-lockfiles GOOD BAD --test NODE   # from two lockfiles (use case 1)
regressleuth validate my_incident/incident.yaml    # every schema problem, with its location
regressleuth inspect  my_incident/incident.yaml    # what would be searched; runs nothing
regressleuth diagnose my_incident/incident.yaml --format json --output result.json
regressleuth report result.json --format html --output report.html
regressleuth noise-scale my_incident/incident.yaml # calibrate noise_scale for noisy metrics
regressleuth manifest-diff . GOOD_REF BAD_REF deploy/artifacts.json   # compare Git manifests, runs nothing
```

Exit codes: `0` verified, `2` not verified (inferred, inconclusive, unresolved, invalid baseline), `3` invalid input, `4` evaluation error, `5` assumption violated. Useful in CI.

```yaml
version: "1.0"
id: risk-api-2026-10-03
good: {model: "risk-model:v1", feature_assembler: fa-1.4, threshold_config: t-0.50}
bad:  {model: "risk-model:v2", feature_assembler: fa-2.0, threshold_config: t-0.45}
metric: {name: accuracy, direction: higher_is_better, regression_threshold: 0.05}
replay: {repeats: 1}                 # noisy metric: interval: anytime + noise_scale
search: {strategy: adaptive, max_cause_size: 2}
budget: {max_replays: 16, audit: extended}
cases: cases.jsonl
adapter: {type: http, base_url: "${SERVICE_URL}", mode: predict}
```

References:
- [Incident specification](docs/INCIDENT_SPEC.md), with a JSON Schema: `regressleuth schema incident`.
- [Adapters](docs/ADAPTERS.md): `command`, `python`, `http`, and `docker` (experimental).
- [Result format](docs/RESULT_SCHEMA.md).
- [Tutorial](docs/TUTORIAL.md).

## How it works

1. Replay the all-good and all-bad states. If they do not separate, stop (`invalid_baseline` or `inconclusive`).
2. Consider every candidate cause: each changed component and each pair (and each triple with `max_cause_size: 3`).
3. Replay the combination whose outcome splits the remaining candidates most evenly; each result rules out the candidates that predicted the opposite.
4. When one candidate remains, verify it: its own combination fails and every smaller subset passes.
5. Audit the cause model with extra replays. Any contradiction gives `assumption_violated`, and no cause is reported.

All six strategies (adaptive, ddmin, random, greedy, exhaustive, one factor at a time) share the same driver, budget accounting, verification and audit. Details: [docs/METHOD.md](docs/METHOD.md).

**Statuses:** `verified` · `inferred` (leading suspect, some checks could not run) · `inconclusive` (noise hid the effect) · `unresolved` (several causes remain) · `invalid_baseline` (no regression on these cases) · `assumption_violated` (no safe single answer) · `evaluation_error` (a replay failed). They are never collapsed.

**Assumptions** listed in every report, with whether each was checked:
- the same labeled cases are scored in every replay;
- replays depend only on the declared versions and the seed;
- the regression has one minimal cause of at most `max_cause_size` components;
- failure is monotone (checked by the audit);
- noise stays within the declared bound;
- unbuildable mixes are reported as incompatible.

[What `verified` means](docs/VERIFICATION.md).

**Noisy metrics.** With `interval: anytime` and a declared `noise_scale`, P(a `verified` set is not a true minimal failing set) <= 1 - `confidence`, for any strategy, budget, audit setting or stopping rule. This assumes independent, sub-Gaussian run noise within that scale ([proof](docs/VERIFICATION.md#diagnosis-level-error-control-interval-anytime)). Without a declared bound, noisy results stop at `inferred`.

## Evidence so far

Every suite below was built in this repository and reported in full, including failures. Pre-registered studies were frozen before their data was seen and evaluated once. [Full protocols and tables](docs/BENCHMARKS.md).

| suite | what it shows |
|---|---|
| development: 22 incidents (20 real models: tabular, text, image, pandas 2 vs 3, noisy) | adaptive verified 95% at 8 isolation replays, ddmin 73%; designed together with the method |
| **holdout: 7 sealed incidents** reconstructed from documented library pitfalls | adaptive 6/7 at 8 replays (95% CI about 42–100%), ddmin 4/7; differs on 2 incidents (p = 0.5) and depends on tie-break order (78.6% vs 50.0% over all name orders); 0 wrong `verified` |
| pairs (development / holdout) | at 8 replays adaptive 91% / 80%, ddmin 45% / 40%, one factor at a time 0% |
| non-monotone controls | the old `full` audit wrongly verified in 31 of 60 runs; the default `extended` audit caught these known cases at 2–3 times the replays (in-sample) |
| external historical pilot: 9 public pandas, scikit-learn and Pillow bugs | 0 wrong `verified` in 675 runs; all single-component, so it validates the pipeline, not the search |
| two dependency-drift studies: 80 public candidates | **0 eligible multi-component incidents** under pre-registered rules; reasons documented |
| noise-bound simulations: 194,400 investigations | `anytime`: 0 wrong `verified`. Student-t, near the threshold: 98 of 3,600 wrong, hence the safer default |
| large search spaces (8–12 components): 54,000 synthetic investigations | 0 wrong `verified`; adaptive far better for pairs, ddmin slightly cheaper for single causes; the audit dominates cost (about 131 replays at 12) |

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/accuracy_vs_budget_dark.svg">
  <img alt="Two line charts of correct verified diagnoses versus replay budget for the development and holdout suites; adaptive reaches 95% at budget 8 on development and 100% at budget 12 on holdout." src="docs/figures/accuracy_vs_budget_light.svg">
</picture>

Have a public regression with pinned good and bad artifacts and a fixed test? The [external incident guide](docs/EXTERNAL_INCIDENTS.md) explains how to contribute it to a future pre-registered study.

## What it does not claim

- It is **not** causal discovery. `verified` means verified under the configured replay model, assumptions and audit checks.
- It is **not** a new search algorithm. Delta debugging over version changes, probabilistic delta debugging, group testing, generalized binary search and pipeline root-cause tools such as BugDoc already exist ([related work](docs/RELATED_WORK.md)). What it may add is practical: explicit verification and abstention, an audited cause model, a diagnosis-level noise bound, and lockfile-hybrid replay.
- Its advantage over delta debugging is measured only on incidents in this repository, most of them author-built. No external multi-component incident has been found yet.

## Limitations

- **Evidence:** the holdout has 7 author-built incidents. The external pilot is single-component only. Two drift studies found no eligible multi-component incident.
- **Search efficiency:** real incidents tend to have 3 to 5 changed components, where exhaustive search is affordable, and the gain over ddmin is modest there. For a single cause, ddmin is slightly cheaper.
- **Audit cost:** the `extended` audit dominates at 10 to 12 components (about 90 to 130 extra replays). At most 12 components are supported.
- **Unchecked combinations:** `verified` covers only the replays run. The audit can miss untested non-monotone combinations, and causes of more than three components are not searched.
- **Noisy metrics:** `verified` needs `interval: anytime` and an honest `noise_scale`. That costs extra runs, and near the threshold it abstains.
- **Reproducibility:** replays must be reproducible from the declared versions and seed. Coupled changes are refused as `invalid_baseline`. Lockfile replays need uv and cannot install local path dependencies or git sources.
- **Docker:** the Docker adapter is tested only against a fake `docker` executable.
- **Safety:** replays run your code without a sandbox, so use them only on trusted code ([SECURITY.md](SECURITY.md)).

## Installation

```bash
pip install -e .                 # core: Python + PyYAML
pip install -e ".[lockfiles]"    # dependency-upgrade incidents (uv, packaging)
pip install -e ".[demo]"         # scikit-learn examples and the HTTP service demo
pip install -e ".[text-demo]"    # Hugging Face text examples
pip install -e ".[dev]"          # tests, coverage, linters, build tools
```

## Reproducibility

```bash
pip install -e ".[demo,dev,lockfiles]"
pytest --cov=regressleuth                                   # 214 tests, about 93% coverage
python benchmarks/freeze_method.py verify                   # frozen method behavior unchanged
python benchmarks/seal.py verify benchmarks/holdout
python benchmarks/reproduce_frozen.py --output /tmp/regressleuth-frozen-reproduction
python benchmarks/historical/verify_snapshot.py             # historical pilot, rerun from its frozen source
python benchmarks/snapshot.py verify benchmarks/drift       # drift study: seal plus frozen source
python benchmarks/snapshot.py verify benchmarks/lockdrift   # lockfile-update study: seal plus frozen source
regressleuth bench                                          # synthetic suite
```

Rebuilding replay tables from scratch (models, data, interpreters) is described in [docs/BENCHMARKS.md](docs/BENCHMARKS.md#reproduce).

## Citation and license

See [CITATION.cff](CITATION.cff) (Avdhesh Mishra, 2026). [Changelog](CHANGELOG.md), [contributing](CONTRIBUTING.md), [roadmap](docs/ROADMAP.md). Apache-2.0 ([LICENSE](LICENSE)).
