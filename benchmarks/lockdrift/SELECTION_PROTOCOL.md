# Lockfile-update incident protocol (dependency drift, version 2)

**Frozen before candidate search** (2026-10-13 IST, 2026-10-12 UTC). `FREEZE_MANIFEST.json` hashes this
text, the Regressleuth method files, and the lockfile modules (`lockfiles.py`,
`lockfile_runner.py`) that define and replay these incidents. This text is not edited
after the first candidate is logged; clarifications go in dated addenda.

## Why a second version

The first dependency-drift study (`benchmarks/drift`) found no eligible incident among 40
candidates. Most disputes came from its date rule: reports filed weeks after a release
put the break inside the "good" state. Its wheels-only rule also excluded packages
published only as source. A lockfile-update pull request has neither problem. The
lockfile at the PR's base and the lockfile at its head *are* the good and bad states,
exactly, and they usually change several distributions at once.

## Population and search

Public GitHub pull requests opened by Dependabot or Renovate that change a committed
lockfile (`uv.lock`, `poetry.lock`, or a requirements file of exact pins) in a Python
project depending on at least one of numpy, pandas, scipy, scikit-learn, pyarrow, polars,
torch, tensorflow, jax, xgboost, lightgbm, statsmodels or transformers. A CI check of the
pull request must have failed, and it must have been created before 2026-10-12. Queries
run through the GitHub issue-search API and are logged in order in `SEARCH_LOG.md`.
Candidates are screened in listed order and every examined candidate is logged in
`CANDIDATES.jsonl`, exclusions included. Intake stops at 40 logged candidates or 15
included incidents with two or more components, whichever comes first.

## Transition

- **Base and head.** The head is the PR's head commit (`refs/pull/N/head`). The base is the
  parent of the bot's first commit on the branch. The diff between them may touch only
  dependency files (lockfiles, requirement files, dependency tables in `pyproject.toml`);
  otherwise the candidate is excluded as `not_dependency_drift`. The project is tested at
  the base commit.
- **States.** The good and bad pins are the lockfile at base and at head, read by
  `regressleuth.lockfiles` (the file the CI test job installs, when there are several).
- **Python.** The first version in the CI test job that is 3.11 or 3.12, else
  `python_unavailable`.
- **Components.** Every distribution whose pin differs, with no grouping. One component
  is reported separately; more than 12 is `search_space_above_cap`.
- **Replays.** `python -m regressleuth.lockfile_runner`. The project is installed editable
  without dependencies, unless CI tests it without installing it. Source distributions may
  be built. Every replay gets the fixed, complete IANA time-zone database used in version 1
  (`tzdata==2025.2` via `PYTHONTZPATH`).

## Fixed tests

The CI test job's pytest selection (paths and `-m`/`-k` filters) runs once in each endpoint
environment, with a JUnit report. The fixed tests are the node IDs that pass in the good
state and fail or error in the bad state: the first 20 in report order if there are more.
They are chosen from these two endpoint runs only, before any mixed-version replay and
before any Regressleuth search. Both endpoints are then rerun twice with exactly those
tests. Good must pass and bad must fail every time; otherwise the candidate is `disputed`
(not reproduced, or not deterministic). If no test differs, it is `disputed` too.

## Eligibility codes

`outside_population`, `not_dependency_drift`, `no_lockfile`, `python_unavailable`,
`build_infeasible` (an endpoint environment or the project cannot be built),
`no_test_command` (the CI tests do not run under pytest), `search_space_above_cap`,
`duplicate_transition`, `unavailable` (repository or pull-request refs not retrievable).

## Ground truth and evaluation

Every one of the `2^k` masks is replayed once with the fixed tests. Ground truth is the
set of strict and coupled minimal failing sets, as defined in version 1, addendum B3. It is
computed from that table, never from Regressleuth output. An incident with neither is
`disputed`. The report blames nothing in particular (a bot PR lists every update), so
there is no blame-agreement rule.

After sealing, all six strategies read the sealed tables once. Budgets are 4, 6, 8, 12, 16,
24, 32 and the full space; random search uses seeds 0–9; the defaults apply (`extended`
audit, causes of at most two components). The pre-registered decisions are those of
version 1. **Search advantage** needs adaptive to win more `k >= 3` incidents than ddmin
on isolation replays before a correct `verified` at the full budget, with an exact two-sided
sign test p < 0.05. **Interaction evidence** needs at least one incident with a minimal
failing set of two or more components, diagnosed as a correct `verified` by at least one
strategy at the full budget. **Large spaces** (`k >= 8`) are reported separately. Wrong
`verified` diagnoses are reported first. Nothing is tuned after the results.
