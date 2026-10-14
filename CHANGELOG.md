# Changelog

## 0.1.0a1 - alpha, unreleased

### Final release hardening (2026-10-14)

- Requirements-style lockfiles now reject trailing unparsed text and conflicting pins active for the target Python, instead of silently accepting or overwriting them.
- `noise-scale` reports a clean input error for an invalid calibration level or a zero-variance sample, which cannot yield the positive scale required by `interval: anytime`.
- CI and the release gate run the bundled pandas-upgrade example with real uv on Python 3.11 and require a `verified` pandas diagnosis under the extended audit in eight replays.
- Related-work citations formerly marked as recalled from memory were linked to source pages or removed; the Dasgupta venue year was corrected.

### Release and evidence workflow (2026-10-11)

- Added a no-cost static Space template with eight precomputed engine reports from two existing synthetic incidents; no paid API, server, or model hosting is needed. The live Gradio template remains available for local use or paid hosting.
- Added `manifest-diff` for read-only comparison of JSON artifact maps at two pinned Git commits. Default output hides values; `--include-values` shows redacted local mappings. The command does not replay artifacts or change any benchmark configuration.
- Added a repeatable wheel/sdist content audit to CI and release builds; it checks for common credential patterns, machine-specific paths, prompt/private files, caches, weights, and datasets. A manual release workflow now builds without publishing unless `publish_testpypi` is explicitly selected.
- Added an external incident submission guide and issue template to collect immutable good/bad states, fixed tests, hybrid feasibility, and independent cause evidence for a future separately pre-registered study. No benchmark cases or frozen method code changed.

### Dependency-drift study (2026-10-11)

- Pre-registered 40-candidate public dependency-drift search, sealed after screening and controlled replay. Thirty-three candidates were excluded and all seven replayed candidates were disputed (six good states failed; one bad state passed). No incident was eligible, so the one-time evaluator produced zero strategy rows and no external evidence for search or interaction claims. The full candidate ledger and dispute reasons are retained.
- The drift evaluator now refuses to overwrite any partial or complete result file, and its seal ignores generated Ruff caches. The historical pilot seal and frozen results remain unchanged.

### Release review (2026-10-13)

- **Sealed studies stay verifiable as the library changes.** `benchmarks/snapshot.py` archives each study's frozen source files and re-runs its `harness.py verify` from that archive. CI and the release workflow use it for both drift studies; the historical pilot keeps its own `verify_snapshot.py`.
- **Lockfile incidents:** `-e .` lines (the project itself, as pip-compile writes it) are accepted. Custom package indexes named in the lockfile (for example PyTorch's CPU index in `uv.lock`, a legacy source in `poetry.lock`, `--extra-index-url` in requirements) are passed to uv. Virtual-environment paths work on Windows. Project paths across Windows drives fall back to absolute.
- `regressleuth noise-scale` warns when the regression threshold is under four times the noise bound, where anytime replays often end inconclusive.
- The dev extra installs `packaging` and, on Python 3.10, `tomli`, which the TOML lockfile readers need.
- README reorganized around the two practical use cases, with the evidence condensed into one table; the case study, adapter guide, and security notes were updated.

### Lockfile incidents (2026-10-12)

- **Lockfile-update study (drift v2), sealed and evaluated once:** 40 failing Dependabot or Renovate lockfile pull requests were logged under a protocol frozen before the search. 37 were excluded and 3 replayed. No test separated the good state from the bad one, so 0 incidents were eligible. Two lockfile-reader defects were found and fixed in dated addenda before any test ran.
- `docs/RELATED_WORK.md` maps the prior work (delta debugging over changes, ProbDD, group testing for complexes and inhibitors, generalized binary search, BugDoc, confidence sequences, breaking-update benchmarks) and states what is and is not new.

- **`regressleuth init DIR --from-lockfiles GOOD BAD --test NODE`** builds a runnable incident from two dependency lockfiles. Supported formats: requirements-style pins (markers evaluated, hashes ignored), `uv.lock` and `poetry.lock`. Each changed distribution becomes a component, and `--group` merges an upgrade with the dependencies it dropped. The project path is stored relative to the incident.
- **`python -m regressleuth.lockfile_runner`** installs each version mix into a cached virtual environment with uv (optional `[lockfiles]` extra). It checks installed files against their wheels' RECORD hashes, reports uninstallable or conflicting mixes as incompatible, counts a test module that cannot be collected as a failure, and rebuilds environments left unfinished by an interrupted run.
- `examples/lockfile_upgrade`: a real pandas 2.3.3 to 3.0.0 upgrade among five changed distributions, `verified` as pandas after 8 replays.
- Lockfiles are read for the target Python and platform: `uv.lock` is walked from its workspace along edges whose markers hold, `poetry.lock` packages are filtered by their markers (group-scoped markers included) and Python range, and git or URL sources are rejected clearly. The first version ignored markers, so it would have installed, for example, numpy for Python 3.12 into a 3.11 environment.
- **`regressleuth noise-scale INCIDENT`** runs the good state on calibration seeds and suggests a `noise_scale`: a 99% chi-square upper bound on the run-to-run SD.

### Error control and scale (2026-10-11)

- **`interval: anytime`** with a declared `noise_scale`: anytime-valid confidence sequences (Robbins' normal mixture) for every mask mean, error split over all `2^k` masks. Proven bound P(wrong `verified`) <= 1 - `confidence` for any strategy, budget, audit and stopping rule, under independent sub-Gaussian noise. The good baseline gets all its runs up front, and a pooled-SD safeguard withholds `verified` when the declared scale is plainly too small. `diagnose(..., noise_scale=...)` uses it.
- **Safer default for noisy metrics:** results judged by per-comparison Student-t intervals now stop at `inferred` when runs vary. A pre-registered simulation (v2) produced wrong `verified` results with those intervals (98 in 3,600 near the threshold) and none with `anytime`. The frozen `normal` profile is unchanged, and all 1,872 frozen traces still reproduce.
- **Pre-registered studies, each run once:** noise guarantee v1 (151,200 investigations; v1's healing scenario was mis-specified and is reported as such), v2 (43,200) and a large-search-space study at 8/10/12 components (54,000). Adaptive search is much better for pair causes and slightly worse than ddmin for single causes; the `extended` audit dominates cost at 12 components.
- **Fix:** with one changed component, reports say every combination was replayed instead of "survived the audit", and list the monotone check as checked.
- The historical pilot is now verified from an archive of its frozen source (`verify_snapshot.py`), so later library changes do not break its check.

### External historical pilot (2026-10-10)

- **Selection protocol frozen before the search** (`benchmarks/historical/`), with source hashes, a 30-candidate ledger, coded exclusion reasons, and a dated addendum (matched runtimes, `excluded` versus `disputed`, one-time reporting). The library code was not changed.
- **Matched environments**: each good/bad pair shares Python 3.11 and every pinned dependency except the studied library; `setup_envs.py` records `ENVIRONMENTS.lock.json` and rejects a pair whose package sets differ in anything else (it caught scikit-learn 1.9's new `narwhals` dependency before reproduction). Every environment must pass `pip check`.
- **Result**: 30 logged, 21 excluded, 9 reproduced (0 disputed), 9 sealed; all six strategies at every budget gave 0 wrong `verified` diagnoses in 675 runs. Every eligible incident had one changed component, so this validates the end-to-end pipeline, not search or interaction diagnosis; no public report qualified with two or more changed components.
- The evaluator refuses to overwrite existing results and the harness refuses to replace a seal.

### Release preparation (2026-10-09)

- **Method freeze**: `benchmarks/frozen/` records source hashes, hyperparameters, replay semantics and a behavioral fingerprint of 1,872 replay sequences. `freeze_method.py verify` confirms the historical behavior is unchanged. Benchmark helpers explicitly select the frozen `full` audit and normal interval; user defaults are safer.
- **Incident Specification 1.0** (YAML or JSON) with a strict validator that reports every problem with its location, duplicate-key detection, a published JSON Schema, and `regressleuth validate` / `regressleuth schema`.
- **Adapters** with one replay contract and classified errors: `command`, `python`, `http` (predict and evaluate modes, header or body version routing) and an **experimental** `docker` adapter (tested only against a fake docker executable).
- **Result schema 1.0** with states, candidate-elimination path, effective verification configuration, assumptions with check status, budget use, errors, runtime and adapter metadata; JSON Schema published. Reports omit component values by default and exclude replay stdout/stderr and exception text. `report.values: redacted` may expose nonsecret version values.
- **Statuses**: `replay_error` renamed `evaluation_error`; new `inconclusive` (noise prevented a conclusion). Exit codes unchanged.
- **CLI**: `diagnose` (with `investigate` kept as an alias), richer `inspect` (search space, singleton/pair/triple counts, budget, adapter, assumptions; runs nothing), `--max-cause-size`, `--audit extended`, `--diagnostics-dir`.
- **Safe product defaults**: `audit: extended` (also checks pairs added to the cause and other components alone) and Welch Student-t intervals for repeated noisy metrics. `full` and `normal` remain explicit historical reproduction options. Causes of up to three components remain opt-in (`max_cause_size: 3`).
- **Holdout benchmark**: 7 pre-registered, sealed incidents reconstructed from cited real-world behavior, plus a sub-threshold control; evaluated once with the frozen method.
- **Higher-order benchmark**: 4 three-way interactions on real models and 2 real non-monotone controls (cancelling pair, healing change).
- **Fair evaluation harness** (`benchmarks/evaluate.py`): identical stored observations for every strategy, budgets 4/6/8/12/full, `exhaustive_order` labeling, suites reported separately, controls checked for false verification.
- **HTTP service demo** with known-good and regressed releases diagnosed purely over HTTP.
- **Negative results documented**: the frozen audit falsely verified a cause in 31 of 60 strategy-by-budget configurations on two real non-monotone controls; the new default had zero false verifications on these known controls, at higher replay cost. The frozen normal interval is too narrow with very few repeats; the Pillow default-filter change produced no material regression and became a control.
- **Secondary release-safety evaluation**: development and holdout suites rerun with the new product defaults, separate from unchanged published frozen results; correct verification did not fall, while total replay cost rose.
- Test suite with 95% coverage (including the optional HTTP demo integration), `ruff check`, `ruff format`, `mypy --strict`, build and `twine check` clean; sdist allowlist.

### Earlier in 0.1.0a1

- **Noisy metrics:** `repeats`/`max_repeats`/`confidence` per incident; replays are judged by a confidence interval and may be `inconclusive`. The runner receives the run `seed`.
- **Monotonicity audit:** after a minimal cause is found, extra replays test the model's assumption. A contradiction yields the new status `assumption_violated` (exit code 5) and withholds the cause; an incomplete audit yields `inferred`. `--audit` and `audit=` control it.
- **Environment versions:** `replay.interpreters` maps an environment component to interpreter paths, so library upgrades are replayable.
- **Hands-on tooling:** `regressleuth demo` (bundled offline example), `regressleuth init` (runnable template), `diagnose(good, bad, run)` for notebooks, text/Markdown/HTML reports with a replay-lattice diagram and next-step advice, a quickstart notebook, Hugging Face Space source, tutorial and method documents.
- **Evidence:** 22 replay incidents (20 on real models: tabular, text, image, environment, noisy) with ground truth proven by exhaustive replay, real-model controls, an expanded synthetic suite with noisy incidents and healing controls, and regenerated figures.
- Reports use result schema version 1.0 (with audit, runs and isolation replay accounting).

- Refactored diagnosis into one shared driver with six replay-selection strategies: adaptive, exhaustive, random, one factor, greedy and ddmin. `--strategy` and `--seed` were added to the CLI.
- Added SleuthBench-synthetic (`regressleuth bench`): 23 valid incidents (15 single-cause, 8 pair interactions) and 5 honesty controls, with budget curves, bootstrap intervals and raw per-incident results.
- Added real-model incidents: scikit-learn tabular models and Hugging Face SST-2 text classifiers, each verified against ground truth by exhaustive replay (`benchmarks/validate_fixtures.py`) and compared across strategies (`benchmarks/run_real.py`).
- CI now runs lint, strict type checks, tests, fixture validation and the synthetic benchmark.

## 0.0.1

- Validated incident manifests, local command replay over fixed cases, adaptive search for single and pair causes, JSON/Markdown/HTML reports, Python API and CLI, and two deterministic churn fixtures.
