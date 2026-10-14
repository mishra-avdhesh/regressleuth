# Tutorial: find what broke your model

You shipped a release and a metric dropped. Several things changed at once: model, preprocessing,
config, data export, a library version. Regressleuth replays *mixes* of the old and new versions
on your fixed evaluation cases and tells you the smallest set of changes that reproduces the
drop, using far fewer runs than trying every combination, and says so when it cannot be sure.

## 1. See it work (no setup)

```bash
pip install -e .
regressleuth demo
regressleuth demo --format html --output report.html
```

The bundled example is a keyword sentiment classifier whose tokenizer stopped lowercasing and
whose notification step started UPPERCASING text. Neither change breaks it alone; together they
do. The report shows the good and bad state, every combination tried, how the candidate causes
were eliminated, and which assumptions were checked.

## 2. From a notebook or script

```python
from regressleuth import diagnose

good = {"model": "v4", "preprocessing": "a1b2c3", "config": "c_old", "data": "2026-09"}
bad = {"model": "v5", "preprocessing": "d4e5f6", "config": "c_new", "data": "2026-10"}


def run(components):  # components[name] is the good OR bad version
    model = load_model(components["model"])
    ...  # build the pipeline from the chosen versions
    return accuracy_on_fixed_cases(model)  # SAME cases and labels on every call


report = diagnose(good, bad, run, threshold=0.03, budget=16, audit="extended")
print(report.summary())
```

Rules that keep the answer meaningful:

- **Fix the evaluation cases.** Every call scores the same labeled cases with the same metric.
  Swapping the data version changes the features of those cases, not which cases you score.
- **`threshold`** is the drop that counts as a regression (`direction="lower_is_better"` for
  error rates or latency).
- **Unbuildable mixes**: raise `regressleuth.errors.IncompatibleReplay`; it is recorded as
  unusable, never mistaken for a pass.

## 3. From the command line

```bash
regressleuth init my_incident
regressleuth validate my_incident/incident.yaml   # schema check, every problem with its location
regressleuth inspect  my_incident/incident.yaml   # candidate causes, search space, budget; runs nothing
regressleuth diagnose my_incident/incident.yaml   # works out of the box on a placeholder pipeline
```

Then edit three things:

1. `incident.yaml`: your real `good` and `bad` versions (any JSON values: paths, git SHAs, config
   dicts), the metric and threshold. Reference: [INCIDENT_SPEC.md](INCIDENT_SPEC.md).
2. `runner.py`: `load_system(components)` and `predict(system, case)`. It is called once per
   replay with a state file (`components`, `cases`, `metric`, `seed`) and writes
   `{"metric": number}` or `{"status": "incompatible"}`.
3. `cases.json`: your fixed labeled cases.

## 4. Read the result

| Status | Meaning | Do this |
|---|---|---|
| `verified` | the named change(s) alone reproduce the drop, smaller subsets do not, and the audit found no contradiction | fix or roll back that component |
| `inferred` | best explanation, but some checks could not run | leading suspect; raise the budget or make hybrids runnable |
| `inconclusive` | noise hid the effect | more repeats, more cases, `interval: student_t` |
| `unresolved` | several explanations still fit | raise the budget or shorten the change list |
| `assumption_violated` | results contradict a small monotone cause; no cause reported on purpose | inspect the contradicting replays; try `max_cause_size: 3` |
| `invalid_baseline` | good and bad do not separate | check cases, threshold, and that the bad state regresses |
| `evaluation_error` | a replay failed | rerun with `--diagnostics-dir DIR` to see its output |

Exit codes for CI: `0` verified, `2` not verified, `3` invalid input, `4` evaluation error,
`5` assumption violated. What `verified` guarantees, exactly: [VERIFICATION.md](VERIFICATION.md).

## 5. Noisy metrics

```yaml
replay: {repeats: 3, max_repeats: 24, confidence: 0.95, interval: anytime, noise_scale: 0.004}
```

Each combination runs `repeats` times; undecided ones get more runs up to `max_repeats`, and the
runner receives `seed` (the repeat index). Two modes:

- **`interval: anytime` with `noise_scale`** (recommended): every mask mean gets an anytime-valid
  confidence sequence, so stopping early is allowed, and a `verified` result carries a bound:
  P(wrong verified) <= 1 - `confidence`, if the runs are independent and their noise is at most
  `noise_scale` (sub-Gaussian; Gaussian with that SD qualifies). Get `noise_scale` by running the
  good state under several seeds and rounding the SD up. It costs more runs, and close to the
  threshold it abstains (`inferred` or `inconclusive`) rather than guess.
- **`interval: student_t`** (default when no noise bound is declared): Welch intervals per
  comparison. A pre-registered simulation produced wrong `verified` results with them near the
  threshold, so a noisy incident in this mode ends at most `inferred`.

The same API: `diagnose(good, bad, run, repeats=3, max_repeats=24, noise_scale=0.004)`.

Not sure what `noise_scale` to declare? `regressleuth noise-scale incident.yaml --runs 10`
runs the good state ten times with calibration seeds (1000 and up, never used by the
diagnosis). It prints the SD and a 99% upper confidence bound for it, ready to paste.
The bound assumes roughly Gaussian run-to-run noise; using it adds 1% to the diagnosis
error bound. If the calibration runs show no variation, use deterministic replay or
provide a justified positive noise bound; the helper will not suggest zero.

## 6. Library and environment versions

```yaml
good: {environment: pandas2, preprocessing: v1}
bad:  {environment: pandas3, preprocessing: v2}
adapter:
  type: command
  command: ["{python}", "runner.py", "--state", "{state}", "--result", "{result}"]
  interpreters: {component: environment, map: {pandas2: envs/pandas2/bin/python, pandas3: envs/pandas3/bin/python}}
```

`{python}` becomes the interpreter of the selected environment. The repository's
[environment demo](../examples/real_env) reproduces a real failure this way.

### From two lockfiles

When the change is a dependency upgrade, skip the runner entirely:

```bash
pip install "regressleuth[lockfiles]"          # adds uv
regressleuth init incident --from-lockfiles good.txt bad.txt --project . \
    --test tests/test_x.py::test_y [--test ...] [--python 3.11] [--group a,b] [--wheels-only]
regressleuth diagnose incident/incident.yaml
```

Every distribution whose pin differs between the lockfiles becomes a component (`absent`
if it was added or removed). Each replay builds, or reuses, a virtual environment in
`incident/.regressleuth-envs/` with exactly that mix of pins. The project is installed
editable without dependencies (`--no-install-project` tests the checkout as is). The named
tests are then run; every one must pass. Mixes that cannot be installed are
`incompatible`. When an upgrade drops dependencies (pandas 3 dropped pytz), group them
with it: `--group pandas,pytz,tzdata`. Otherwise the uninstallable mixes leave the
audit incomplete and the result is `inferred`. At most 12 components; split larger
upgrades. See [examples/lockfile_upgrade](../examples/lockfile_upgrade).

## 7. A running service

```yaml
cases: cases.jsonl          # {"input": {...}, "label": ...} per line
adapter: {type: http, base_url: "${SERVICE_URL}", mode: predict, components_via: header}
```

The service must serve a requested mix of versions for one request (canary or feature-flag
routing); see [the HTTP service demo](../examples/http_service) and [ADAPTERS.md](ADAPTERS.md).

## 8. Strategy, budget and audit

`adaptive` (default) picks the most informative replay each step; `ddmin` is classic delta
debugging and is competitive; `exhaustive`, `random`, `greedy` and `one_factor` are baselines
(`one_factor` cannot find interactions). The budget counts the two endpoint replays plus search
and verification; 12 to 16 resolves most incidents with 4 to 8 changed components. The audit
adds replays on top: `extended` (the new default) or `full` (the cheaper historical profile).
The stronger audit costs roughly two to three times as many total replays on the current suites,
and it can still miss untested combinations.

## 9. In CI

```yaml
- run: regressleuth diagnose incident.yaml --format markdown --output report.md
  continue-on-error: true
- uses: actions/upload-artifact@v4
  with: {name: regression-report, path: report.md}
```

## Safety

The replay command is code you wrote, run as a local subprocess with a timeout. It is not
sandboxed: only point Regressleuth at code you trust. Reports contain component names, versions
(secret-looking values redacted), metrics and outcomes, never stdout, stderr or exception text.
