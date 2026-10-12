# Dependency-drift incident selection protocol

**Frozen before candidate search:** 2026-10-11 IST (2026-10-10 UTC). `FREEZE_MANIFEST.json`
records SHA-256 hashes of the Regressleuth method files (engine, strategies, statistics,
models, specification, adapters) at this point. This text is not edited after the first
candidate is logged; clarifications go in a dated addendum that leaves this text visible.

## Why this population

The historical pilot found that public reports almost always describe one library
upgrade, so every eligible incident had one changed component. A *dependency-drift*
incident is different by construction. A project's tests start failing although its own
code did not change, because an unpinned dependency released a new version. Between the
last passing and the first failing run, several packages usually changed at once. Only
one change, or a combination, is responsible, and the others are bystanders that
nobody chose. That is the multi-component search problem Regressleuth addresses.

## Population and search

Public GitHub issues or pull requests in Python machine-learning or data projects (projects
that depend on at least one of numpy, scipy, pandas, scikit-learn, pyarrow, torch,
tensorflow, jax, xgboost, lightgbm, statsmodels, transformers or polars). Each must report
that tests or CI broke because of a new release of a dependency, with the report dated
before 2026-10-10. Search queries and their order are recorded in `SEARCH_LOG.md`.
Every examined candidate is logged in `CANDIDATES.jsonl` before any reproduction,
including exclusions. Intake stops after 40 logged candidates or 15 sealed incidents with
two or more changed components, whichever comes first. Duplicate reports of the same
transition are one candidate.

## Transition, components and states

- **Project code** is fixed at the last commit on the default branch before the first
  failure (`D_bad`), or at a commit named in the report.
- **Dates.** `D_bad` is the first failure date stated in the report, else its creation
  date. `D_good` is the last passing date stated in the report, else `D_bad` minus 14 days.
- **Requirement set.** This is the project's declared runtime and test requirements at the
  fixed commit, as its CI installs them (extras and requirement files named in the CI
  workflow). It is resolved for Python 3.11 (3.12 if the project does not support 3.11)
  with `uv pip compile --exclude-newer`, at the end of `D_good` and the end of `D_bad`
  (UTC). The two resolutions are the good and bad states.
- **Changed components** are every distribution whose resolved version differs between
  the two states, including additions and removals (an absent package is a value). No
  change is added, dropped or merged.
- **Hybrids** install the exact pinned union with `--no-deps`: changed components in the
  mask at the bad version, the rest at the good version, unchanged packages at their shared
  version. A hybrid is **incompatible** if installation fails or `uv pip check` reports a
  requirement conflict. Incompatible hybrids are recorded as such and never counted as
  passes or failures.
- **Test and metric.** The fixed test is the failing test or tests named in the report
  (pytest node IDs), run on the fixed commit. Metric 1 if they all pass and 0 otherwise;
  higher is better; threshold 0.5. A crash or timeout of the runner itself is a replay
  error. Cases and threshold are fixed before any replay.

## Eligibility and reason codes

A candidate is eligible only if every rule below holds. An exclusion uses these codes:
`no_dated_public_report`, `outside_population`, `not_dependency_drift` (the project code,
CI image, Python version or a pinned dependency changed in the transition),
`no_fixed_test`, `unresolvable_requirements`, `build_infeasible` (compiled project code, or
no wheel for a needed distribution on Linux x86-64), `download_too_large` (more than 1.5 GB
of wheels for the union of states), `search_space_above_cap` (more than 12 changed
components), `duplicate_transition`.

A candidate that passes screening goes to controlled replay. It is **disputed** if the
good state does not pass, the bad state does not fail, or the exhaustive table (below)
contains no minimal failing set that includes a distribution the report blames. A
disputed candidate stays in the ledger with its replays and is excluded from accuracy;
its test and threshold are never changed to make it reproduce. One changed component
(`k = 1`) is kept and reported separately, as in the historical pilot.

## Ground truth

Every one of the `2^k` masks is replayed once (tests are deterministic; a rerun of the two
endpoints checks this) and stored with its status. Ground truth is the set of **minimal
failing sets**: masks that fail while every non-empty proper subset is compatible and
passes. It is computed from this exhaustive table, never from Regressleuth output. The
report's blamed distribution is recorded next to it, and any disagreement is preserved,
not reconciled.

## Evaluation (one time, after sealing)

All six frozen strategies read the same sealed table. Budgets are 4, 6, 8, 12, 16, 24, 32
and the full space, random search uses seeds 0–9, with the `extended` audit, Student-t
interval and causes of at most two components (the defaults). Results are stratified
by `k` (1; 2–4; 5–7; 8–12) and by cause size (single; pair; none within the default
size). Wrong `verified` diagnoses are reported first.

Pre-registered decisions (incidents with `k >= 3`, paired per incident):

1. **Search advantage.** For each incident, compare the isolation replays adaptive and
   ddmin need before a correct `verified` at the full budget, where never verifying counts
   as worse than any count. "Adaptive advantage on external incidents" is claimed only if
   adaptive wins more incidents than ddmin and the exact two-sided sign test over
   non-tied incidents gives p < 0.05. The same test is reported at budgets 8 and 12 as
   secondary results.
2. **Interaction evidence.** Claimed only if at least one included incident has a minimal
   failing set of two or more components and the tool returns it as a correct
   `verified` diagnosis at the full budget with at least one strategy. The rate across
   strategies and budgets is reported.
3. **Large search spaces.** Results for `k >= 8` are reported separately. With fewer than
   three such incidents, the stratum is described, not summarized as a rate.

The method files in `FREEZE_MANIFEST.json` must be unchanged at evaluation. Nothing is
tuned after the results.
