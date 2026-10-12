# Historical incident selection protocol

**Frozen before candidate search:** 2026-10-10 UTC. The pre-evaluation source and
configuration hashes are in `FREEZE_MANIFEST.json`. This protocol must not be edited
after the first candidate is logged. Clarifications, if needed, go in a dated addendum
that leaves the original text visible.

## Objective and population

Sample public ML or ML-adjacent software regressions whose original evidence predates
2026-10-08, the existing Regressleuth benchmark freeze. The unit is one historical
good-to-bad transition, not one issue comment or one replay mask. The pilot target is
10–15 eligible transitions. A smaller pilot is valid if fewer meet the rules. Do not
create extra changed components, failures, or cases to fill the target.

Search public issue trackers, pull requests, release notes, migration guides, and
reproducible bug collections using recorded queries. Log every candidate examined in
`CANDIDATES.jsonl` before attempting reproduction, including exclusions and failures.
Stop candidate intake after the first 30 distinct transitions have been screened or
after 15 eligible incidents have been sealed, whichever occurs first. A duplicate issue
describing the same good/bad transition is one candidate with multiple sources.

## Inclusion rules

An incident is eligible only if all rules hold:

1. Dated public evidence predates 2026-10-08 and describes a real regression or
   compatibility failure independent of this project. Record issue/PR/release URLs and
   dates. A general migration note without a specific affected behavior is insufficient.
2. Exact known-good and known-bad versions, commits, or content hashes are available.
   Both states must be executable on this machine or a documented reproducible runtime.
3. Changed artifacts are enumerated from the historical transition. Their boundaries
   must correspond to independently versioned code, data, model, preprocessing, config,
   runtime, or dependency artifacts. Record all relevant changes, including benign ones;
   do not inject changes to make search harder.
4. The source gives a fixed input/test and expected behavior, or an independently
   specified dataset/metric. Fix cases and threshold before running Regressleuth. For a
   binary historical regression test, use metric 1 for pass and 0 for fail, direction
   higher-is-better, and threshold 0.5. Do not select cases or thresholds after outcomes.
5. Relevant good/bad hybrids can be constructed without silently changing other
   components. Record all infeasible masks and why. For a one-component transition, the
   two endpoints suffice but the case is reported separately from multi-component search.
6. Original issue, upstream fix, or a controlled exhaustive replay independent of the
   search strategies supports the expected cause. Record competing explanations and
   multiple valid minimal causes when present; do not force one cause.
7. The reproduction needs no private data, private service, secrets, or unavailable
   weights, and its artifacts can be redistributed or downloaded under their licenses.

## Exclusion and unresolved rules

Keep a candidate record with one or more exact reason codes:

- `no_dated_public_regression`: source does not establish a historical regression.
- `no_good_state` / `no_bad_state`: an endpoint cannot be reconstructed.
- `uninstallable_dependency`: pinned versions cannot run in a documented environment.
- `unfixed_test`: the original behavior or metric cannot be fixed independently.
- `unbounded_changes`: relevant changed artifacts cannot be enumerated.
- `infeasible_hybrids`: meaningful required combinations cannot be executed.
- `unestablished_cause`: independent evidence and controlled replay do not support a
  defensible cause set.
- `private_dependency`: unavailable data, service, secret, or weights are required.
- `duplicate_transition`: an already logged good/bad transition.
- `license_block`: artifacts cannot be used or reproduced as planned.

An execution failure is recorded, not silently dropped. If the historical explanation
and exhaustive replay disagree, retain the candidate as `disputed`; document both and
exclude it from accuracy denominators until the discrepancy is resolved independently.
An included incident that later defeats Regressleuth stays included.

## Ground truth and sealing sequence

For each candidate, record provenance fields before implementation: ID, title, URLs,
source type/date, exact good/bad versions, changed components, historical cause claim,
root-cause evidence, fixed test, metric, threshold, environment, and hybrid feasibility.
Record source retrieval date, package/file/data hashes, exact commands, and exclusion
reasons as they become available. A source URL alone is not proof of reproducibility.

For eligible incidents, run controlled good and bad endpoints and, where feasible,
every hybrid mask. Store the raw outcomes and a separate `ground_truth.json` before any
strategy evaluation. Ground truth is the set of independently supported minimal causes;
unknown or disputed is represented explicitly. Never derive it from Regressleuth output.

Then hash incident definitions, cases, metrics, thresholds, component mapping,
incompatibility rules, ground truth, and raw replay observations into `SEAL.json`.
Evaluation refuses to run if the seal differs. After sealing, preserve any failure and
record changes only as a new version of the benchmark, not an overwrite.

## Evaluation rules

Evaluate all six frozen strategies on the same sealed observation table, metric values,
noise seeds, incompatibilities, budget semantics, `extended` audit, and Student-t default.
Budgets are 4, 6, 8, 12, and `full` where meaningful; report each incident's search-space
size and mark budgets above that space. Random uses ten fixed seeds 0–9. Record every
strategy-budget row, including errors and wrong verifications. Do not tune search,
audit, intervals, stopping rules, or cause ranking after seeing these results.

Primary outcomes are correct and incorrect `verified`, correct `inferred`, unresolved,
inconclusive, assumption violations, false attribution, isolation/audit/total replays,
runner calls, and wall time. Separate single, pair, and naturally occurring higher-order
causes. Keep this suite separate from development and sealed holdout summaries. Nominal
Student-t confidence applies to one replay comparison, not the final diagnosis.
