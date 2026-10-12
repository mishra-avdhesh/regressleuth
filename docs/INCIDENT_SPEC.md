# Regressleuth Incident Specification 1.0

An incident file describes one regression: the known-good and known-bad version of every
pipeline component, the metric that regressed, and how to replay a mix of versions. It is
YAML or JSON. The machine-readable schema is `regressleuth schema incident`
([`incident-1.0.schema.json`](../src/regressleuth/schemas/incident-1.0.schema.json)); the
reference checker is `regressleuth validate FILE`, which also enforces the semantic rules a
JSON Schema cannot express and reports **every** problem with its location.

```yaml
version: "1.0"                 # required, the string "1.0"
id: churn-2026-10-03           # required: letters, digits, '.', '_', '-' (1-128, starts alphanumeric)
description: Accuracy dropped after the October release.     # optional
metadata: {owner: risk-team, ticket: INC-4211}               # optional, free-form (provenance)

good:                          # required: component name -> version (any JSON value)
  model: models/v4
  preprocessing: {commit: a1b2c3, lowercase: true}
  environment: py312-pandas2
bad:                           # required: the same component names
  model: models/v5
  preprocessing: {commit: d4e5f6, lowercase: true}
  environment: py312-pandas3

metric:                        # required
  name: accuracy
  direction: higher_is_better  # or lower_is_better
  regression_threshold: 0.02   # change that counts as the regression (> 0)

replay:                        # optional: noisy metrics
  repeats: 3                   # runs per replay (default 1)
  max_repeats: 24              # extra runs while inconclusive (default = repeats)
  confidence: 0.95             # interval level, 0.5 <= c < 1 (default 0.95)
  interval: student_t          # default | anytime | normal (historical benchmark option)
  noise_scale: 0.004           # required by, and only allowed with, interval: anytime

search:                        # optional
  strategy: adaptive           # adaptive | ddmin | exhaustive | greedy | one_factor | random
  max_cause_size: 2            # 1, 2 (default) or 3
  seed: 0                      # for the random strategy

budget:                        # optional
  max_replays: 16              # isolation replays incl. both endpoints (default 16, 2..4096)
  audit: extended              # default | full (historical) | integer cap | 0 to skip

cases: cases.jsonl             # optional path (relative to this file) to the fixed labeled cases
report:
  values: omit                 # default | hashed | redacted: how versions appear in reports

adapter:                       # required: how one hybrid is evaluated (see ADAPTERS.md)
  type: command
  command: ["{python}", "runner.py", "--state", "{state}", "--result", "{result}"]
  timeout_seconds: 600
```

## Semantic rules (checked by `regressleuth validate`)

| Rule | Message prefix |
|---|---|
| `good` and `bad` have exactly the same component names | `good.X: missing` / `bad.X: missing` |
| component names match `^[A-Za-z_][A-Za-z0-9_.-]{0,63}$` | `good.X: component names must match` |
| at least one and at most 12 components differ | `bad: no component differs` / `bad: N components changed` |
| values are JSON without NaN or infinity | `good.X: must be a JSON value without NaN` |
| `max_repeats >= repeats` | `replay.max_repeats: must be at least replay.repeats` |
| an `interpreters` / `images` map covers the good and bad value of its component | `adapter.interpreters.map: no entry for bad.X` |
| HTTP `predict` mode needs `cases` and a locally computable metric (accuracy, error_rate, mae, rmse) | `cases: required` / `metric.name:` |
| unknown keys anywhere are errors (catches typos) | `X: unknown key` |
| YAML/JSON duplicate keys are errors, with the line number | `duplicate key 'id' (line 3)` |

## Semantics

- A **component** is anything versioned that the replay can switch: a model artifact, a
  preprocessing commit, a config, a data snapshot, a library environment, a service release.
  Components whose good and bad values are equal are recorded as unchanged and never searched.
  If a JSON map of those versions is committed at both endpoints, `manifest-diff` can
  extract the changed names and pinned IDs; see [Git manifests](GIT_MANIFESTS.md).
- A **replay** evaluates one hybrid: the bad version for a chosen subset of changed
  components and the good version for the rest, scored on the **same** labeled cases.
- The **search** finds the smallest set of components (up to `max_cause_size`) whose bad
  versions alone reproduce a change of at least `regression_threshold` in the stated
  direction. `verified` means verified under the configured replay model, assumptions,
  and audit checks. The bounded guarantee is defined in [VERIFICATION.md](VERIFICATION.md).
- Explicit command-line flags (`--budget`, `--strategy`, `--audit`, `--max-cause-size`,
  `--seed`) override the file.

## Versioning policy

`version: "1.0"` is frozen: a 1.x release may add optional keys but will not change the
meaning of existing ones or make valid 1.0 files invalid. A breaking change gets version
"2.0" and the loader will keep reading 1.0. Pre-1.0 "legacy" JSON manifests (the frozen
development benchmark uses them) are still read. They now inherit the same safe audit and
interval defaults when used directly. Frozen benchmark scripts explicitly select `full` and
`normal`; migrate user incidents to 1.0.

## Noisy metrics: `interval` and `noise_scale`

| `interval` | judgement of one replay | best status for a noisy incident |
|---|---|---|
| `student_t` (default) | Welch interval on the difference from the good baseline | `inferred`: per-comparison intervals bound no diagnosis-level error, so `verified` is withheld whenever runs varied |
| `anytime` | anytime-valid confidence sequences, error `1 - confidence` split over all `2^k` masks | `verified`, with P(the verified set is not a true minimal failing set) <= `1 - confidence` under the stated noise assumptions |
| `normal` | normal interval (historical benchmark profile only) | `verified`, no error bound (kept to reproduce frozen results) |

`noise_scale` is an upper bound on the sub-Gaussian scale of one run's noise. For Gaussian
noise, that is its standard deviation; for a metric bounded in an interval of width `w`, `w/2`
always works. Estimate it from seed-to-seed runs of the good state before the incident,
and round up. A pooled run-to-run SD above twice the declared value withholds `verified`.
Deterministic replays (one run, or runs that never vary) are compared exactly in every mode.
