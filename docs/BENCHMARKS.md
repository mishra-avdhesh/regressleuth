# Benchmarks and evaluation protocol

All numbers here come from files in `benchmarks/results/` and can be regenerated (see the end).
Every suite is reported **separately**; nothing is pooled into one headline.

## Protocol

1. **Freeze.** On 2026-10-08 the search method was frozen before any holdout data existed:
   source hashes, hyperparameters, replay semantics and a behavioral fingerprint of 1,872 replay
   sequences ([`benchmarks/frozen/frozen_method.json`](../benchmarks/frozen/frozen_method.json)).
   `python benchmarks/freeze_method.py verify` re-runs the fingerprint; it still passes on the
   release code. The historical benchmark helpers explicitly select the frozen `full` audit and
   normal interval. Normal user incidents now select `extended` and Student-t by default.
2. **Pre-register and seal the holdout.** The holdout incidents, their sources, the uniform
   threshold rule and the construction rules were written down
   ([`PREREGISTRATION.md`](../benchmarks/holdout/PREREGISTRATION.md)) before data existed.
   Construction problems found by the ground-truth proofs were fixed and logged there before
   any strategy ran. The suite was then sealed by SHA-256 (55 files, `seal.py verify`).
3. **Prove ground truth.** Every incident's cause is proven by replaying all `2^k`
   combinations (several runs each for stochastic incidents): a combination regresses if and
   only if it contains the cause (`prove_ground_truth.py`, `validate_fixtures.py`).
4. **Fair comparison.** Each runner is executed once per (combination, run seed) and stored.
   Every strategy then replays against that same table, so all strategies see identical
   metrics, identical noise realizations and identical incompatibilities, with the same budget,
   driver, verification and audit rules. Tests enforce this.
5. **Evaluate once.** `benchmarks/evaluate.py` runs every strategy at budgets 4, 6, 8, 12 and
   `full` (= `2^k`, enough to enumerate everything). Exhaustive enumeration cut off by a
   smaller budget is labeled `exhaustive_order`; `exhaustive` means the full enumeration.
   Random search uses 10 seeds. The archived report used 95% bootstrap intervals over
   incidents; those intervals are too narrow for all-success binary outcomes in such a small
   suite. The current evaluator uses Wilson intervals for binary incident outcomes, but the
   archived published files have not been changed.

## Suites

| Suite | Incidents | Origin | Independence |
|---|---|---|---|
| development | 22 (20 real-model; 11 pairs) | designed in this project alongside the method | low: mechanisms chosen by the author |
| **holdout** | **7** (5 pairs, 2 singles) + 1 control | reconstructed from documented library behavior, issues and pitfalls (NumPy NEP 50, pandas 3 datetime resolution, pandas `NA` parsing, training-serving skew, `predict_proba` column order, `PYTHONHASHSEED`, time zones) on Adult census, MNIST and seeded synthetic data | medium: cited sources, sealed, method frozen, but still built by the same author |
| higher_order | 4 three-way + 2 non-monotone controls | designed (defense-in-depth failures on real models) | low |
| synthetic | 31 valid + 11 controls | oracle incidents, 5 to 8 components, 8 noisy | none: shares the method's assumptions |
| **external historical pilot** | **9** (all single-component) | public regression reports selected under a protocol frozen before the search; reproduced in matched environments | higher: third-party reports and fixes, predeclared criteria, sealed, evaluated once; screened and built by the same author |
| dependency-drift study | 40 logged; **0 eligible** | public multi-component dependency-drift candidates selected under a pre-registered protocol | no performance evidence: 33 excluded, 7 disputed after controlled replay; sealed and evaluated once |

## Development suite (22 incidents, frozen profile)

| strategy | B=4 | B=6 | B=8 | B=12 | full | mean replays at full |
|---|---:|---:|---:|---:|---:|---:|
| **adaptive** | 32% | 64% | **95%** | 95% | 95% | **5.6** |
| ddmin | 36% | 64% | 73% | 95% | 95% | 6.5 |
| random (10 seeds) | 17% | 39% | 76% | 95% | 95% | 7.0 |
| greedy | 27% | 55% | 64% | 95% | 95% | 7.0 |
| exhaustive_order / exhaustive | 27% | 55% | 64% | 95% | 95% | 12.0 |
| one factor at a time | 27% | 50% | 50% | 50% | 50% | 5.0 |

Verified-and-correct rate. The 5% no strategy verifies is `noisy_labels_x_width_borderline`,
where one audit replay sits 0.01 from the threshold and ends `inferred` (correct cause).

## Holdout suite (7 incidents, sealed, evaluated once with the frozen method)

| strategy | B=4 | B=6 | B=8 | B=12 | full | median / mean replays at full | unresolved at B=8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **adaptive** | 0% | 57% | **86%** | **100%** | 100% | 6 / **6.9** | 0% |
| ddmin | 0% | 57% | 57% | 86% | 100% | 6 / 8.3 | 29% |
| random (10 seeds) | 1% | 7% | 23% | 71% | 100% | 11 / 10.7 | 53% |
| greedy | 14% | 14% | 57% | 86% | 100% | 8 / 9.0 | 43% |
| exhaustive_order / exhaustive | 14% | 14% | 57% | 86% | 100% | 32 / 32.0 | 43% |
| one factor at a time | 14% | 14% | 29% | 29% | 29% | 7 / 6.6 | 71% |

No strategy verified a wrong cause or attributed a healthy component (false attribution 0%)
at any budget. With 7 incidents the uncertainty is large: adaptive at B=8 is 6/7 (exact
binomial 95% interval about 42% to 100%), ddmin 4/7; adaptive won on two incidents and tied on
five (exact paired two-sided p = 0.5). The B=8 outcome also depends on the arbitrary component-name
order that breaks ties in the search: over all 120 renamings of each incident, adaptive verified
78.6% and ddmin 50.0% ([sensitivity analysis](experiments/TIE_BREAK_SENSITIVITY.md)). The one
adaptive miss with the original names is `holdout_proba_column_order`, which ends `inferred` with
the right cause. The Pillow control (a real but 1.3-point regression)
was correctly refused as `invalid_baseline` by every strategy.

## Higher-order suite (4 three-way interactions on real models)

- **Default cause size 2 (frozen profile):** no strategy ever verified a cause; adaptive, ddmin, greedy,
  random and exhaustive report `assumption_violated` at the full budget, one factor `unresolved`.
  The tool does not claim triples it was not asked to search.
- **Opt-in `max_cause_size: 3`:** at the full budget (32) adaptive verifies 4/4 with 12.5 isolation
  replays on average, ddmin 4/4 with 17.8, random 18.6, greedy 22.2, exhaustive 32. At budget 12
  adaptive verifies 1/4 (the other 3 end `inferred` with the right cause). Triples are expensive.

## Controls and the monotonicity audit (Part D)

| Control (real models) | What it does | Runs with a verified cause, frozen `full` audit | `extended` audit |
|---|---|---:|---:|
| `ctrl_tabular_cancelling_pair` | two changes each break it alone and cancel together; a third causes the regression | 5 / 30 | 0 / 30 |
| `ctrl_text_lowercase_heals` | a failing pair is healed by another change in the release; truncation causes the regression | 26 / 30 | 0 / 30 |
| `ctrl_tabular_coupled_scaling` | coupled change, bad state passes | 0 / 30 (`invalid_baseline`) | 0 / 30 |
| `ctrl_env_model_needs_new_pandas` | hybrids that cannot be built | 0 / 30 (`inferred`/`unresolved`) | 0 / 30 |
| `holdout_ctrl_pillow_subthreshold` | real change, below threshold | 0 / 30 (`invalid_baseline`) | 0 / 30 |

(30 strategy-by-budget configurations = 6 strategies x 5 budgets, cause size 2; random
search averages ten seeds in each configuration.) **The frozen audit has a blind spot**: it
only replays combinations next to the candidate, so latent failures elsewhere that another
change hides in the all-bad state go unnoticed; the verified component is the one that fixes
the deployed state, but the monotone model is false. The synthetic suite reproduces this (3
adversarial controls verified by adaptive, ddmin, greedy and one factor; 27% of controls).
The current-default **extended audit** was designed after this result, on these designed controls (not
on the holdout). It removed every unsafe verification in all suites (real: 31 to 0;
synthetic: 27% to 0%) and did not lower verified accuracy on the development or holdout suites.
Its price is replays: holdout total replays for adaptive rise from 11.1 to 21.6, synthetic from
13.2 to 39.6; one noisy synthetic incident drops to `inferred`.

## Synthetic suite (31 valid incidents, 5 to 8 components)

| strategy | B=8 | B=12 | full | mean isolation replays | unsafe verification on 11 controls (full / extended audit) |
|---|---:|---:|---:|---:|---:|
| adaptive | 74% | 100% | 100% | 7.3 | 27% / 0% |
| ddmin | 71% | 81% | 100% | 8.5 | 27% / 0% |
| random | 29% | 63% | 100% | 11.5 | 15% / 0% |
| greedy | 58% | 68% | 100% | 11.3 | 27% / 0% |
| exhaustive_order / exhaustive | 58% | 68% | 100% | 123.9 | 0% (full enumeration) / 0% |
| one factor | 58% | 61% | 61% | 6.9 | 27% / 0% |

The oracle shares the search's assumptions, so this suite measures efficiency under the model,
not realism.

## Noise

The frozen noise rule uses a normal interval. With very few repeats it is anti-conservative
(an unlucky 3-run baseline produced a spurious failure in a unit test). Welch's Student-t
interval (`replay.interval: student_t`) is now the product default. The published frozen
numbers use the normal rule; the secondary safe-default evaluation uses Student-t. The noisy
development and holdout incidents use 6 to 24 and 3 to 9 runs.

## Secondary release-safety evaluation (current product defaults)

The separate run uses `extended` and `student_t` on the same stored observations, without
changing the archived results. It was performed after the audit weakness was found.

| suite | adaptive B=8 correct | adaptive B=12 correct | mean total replays B=8 | false verified controls |
|---|---:|---:|---:|---:|
| development (22) | 21/22 | 21/22 | 11.0 | 0 |
| holdout (7) | 6/7 | 7/7 | 19.4 | 0 |

Across the two real-model non-monotone controls, the current default had 0/60 false-verifying
strategy-by-budget configurations. This is an in-sample check on known
controls. [All rows and strategy summaries](../benchmarks/results/safe_default/EVALUATION.md).

## External historical pilot (9 public regressions, sealed, evaluated once)

[Selection protocol](../benchmarks/historical/SELECTION_PROTOCOL.md) (frozen 2026-10-10 before
any candidate was logged, with source hashes in `FREEZE_MANIFEST.json`),
[dated addendum](../benchmarks/historical/ADDENDUM_2026-10-10.md),
[candidate ledger](../benchmarks/historical/CANDIDATES.jsonl),
[search log](../benchmarks/historical/SEARCH_LOG.md),
[full report](../benchmarks/results/historical/EVALUATION.md).

**Funnel.** Intake stopped at 30 logged candidates (pandas 12, scikit-learn 10, NumPy 3,
Transformers 2, MLflow 1, torchvision 1, one application issue on Pillow; reports dated
2021-02-08 to 2026-10-03, all before the 2026-10-08 method freeze).

| stage | count | detail |
|---|---:|---|
| logged before any reproduction | 30 | every examined transition, including exclusions |
| excluded by the predeclared rules | 21 | `no_good_state` 6, `duplicate_transition` 4, `unfixed_test` 3, `uninstallable_dependency` 3, `no_bad_state` 2, `infeasible_hybrids` 2, `no_dated_public_regression` 1 |
| sent to controlled reproduction | 9 | criteria and threshold (0.5 on a pass/fail metric) fixed at screening |
| disputed (reproduction did not support the report) | 0 | the status exists and stays separate from `excluded` |
| included, reproduced and sealed | 9 | pandas 5, scikit-learn 3, Pillow 1 |

Each good/bad pair ran in two virtual environments with the same Python 3.11 and the same
pinned shared dependencies; the recorded package sets differ only in the studied library
(`setup_envs.py`, `ENVIRONMENTS.lock.json`). The pair check caught one real mismatch before
reproduction: scikit-learn 1.9 added the `narwhals` dependency, so it was installed on the
older side too. Every known-good version passed and every known-bad version failed, with
the failure reported in the issue (for example, the float32 `LinearRegression` residual of
59.06 versus 24.40 in scikit-learn 1.6.0, and pandas 2.2 raising `KeyError: '__deepcopy__'`
on custom `attrs`). That claim-versus-replay check is in each `provenance.json`.

**Outcomes** (all six strategies on the same sealed observations, `extended` audit, Student-t,
budgets 4/6/8/12/full, random over seeds 0–9; 675 strategy-budget-seed runs):

| strategy | wrong verified | correct verified | correct inferred | unresolved | inconclusive | assumption violated | replays per run |
|---|---:|---:|---:|---:|---:|---:|---:|
| adaptive | **0** | 45/45 | 0 | 0 | 0 | 0 | 2 |
| ddmin | **0** | 45/45 | 0 | 0 | 0 | 0 | 2 |
| random (10 seeds) | **0** | 450/450 | 0 | 0 | 0 | 0 | 2 |
| greedy | **0** | 45/45 | 0 | 0 | 0 | 0 | 2 |
| exhaustive | **0** | 45/45 | 0 | 0 | 0 | 0 | 2 |
| one factor at a time | **0** | 45/45 | 0 | 0 | 0 | 0 | 2 |

**What this does and does not show.** Every eligible incident had one changed component, so
its two states are the endpoints. Every strategy therefore runs the same two replays, the
audit has nothing to test, and budgets of 4 or more exceed the search space (marked in
`rows.json`). The result shows that the incident format, matched-environment replay and
verification work end to end on real third-party regressions without a wrong verified
answer. It is not evidence about search efficiency, interactions, or the audit. Per
incident, 9/9 correct has an exact 95% interval of 66% to 100%, and 0/9 wrong verified is
compatible with a rate up to 34%.

The second finding is structural. None of the 30 public reports met the rules with two or
more independently versioned changed components. Public trackers describe regressions at
the level of one library upgrade; multi-component ML pipeline incidents with recoverable
artifacts were not found. External evidence for interaction diagnosis is still missing.

The evaluator refuses to run again once `benchmarks/results/historical/rows.json` exists,
and the harness refuses to replace `SEAL.json`; a change becomes a new benchmark version.
`reproduce.py` writes evidence into the incident folders and must not be run on the sealed
suite; `regressleuth diagnose` on an incident file replays it live without writing there.
The original historical seal accidentally included 11 generated Ruff cache files, which
Git ignores. `verify_snapshot.py` checks the unchanged original seal against the hash in
`RUN.json`, verifies every public evidence file against that seal after excluding those
cache entries, and reproduces the published results byte for byte from the frozen source.
The generated cache bytes are not needed for evaluation and are not part of a clean checkout.

One wording issue was found and left unchanged, because the library is frozen for this
evaluation. With one component, the text report gives the reason "the monotone model
survived the audit" while listing `monotone_failure=not_checked`: no audit replay is
possible when both states have already been observed. The `verified` status is sound
(the whole two-state space was replayed), but the reason text should say so.

## Dependency-drift study (zero eligible incidents)

The [selection protocol](../benchmarks/drift/SELECTION_PROTOCOL.md) and
[addenda](../benchmarks/drift/ADDENDUM_2026-10-11.md) were recorded before the candidate
search. Intake stopped at its pre-registered cap of 40 public reports. The
[sealed report](../benchmarks/results/drift/EVALUATION.md) and
[candidate ledger](../benchmarks/drift/CANDIDATES.jsonl) show the full funnel:

| stage | count | outcome |
|---|---:|---|
| logged | 40 | every screened candidate retained |
| excluded under the recorded rules | 33 | most often an infeasible build or no fixed test; exclusion reason counts overlap |
| sent to controlled replay | 7 | good and bad states fixed before replay |
| disputed | 7 | six good states already failed; one bad state passed |
| eligible and sealed for strategy comparison | **0** | no rows in `results/drift/rows.json` |

The seven disputes remain in the ledger with their original endpoint observations and
specific reasons. The sealed evaluator ran once and produced **zero strategy runs**. Thus
“zero wrong verified” would be misleading for this suite: no diagnosis was attempted. The
pre-registered adaptive-versus-ddmin comparison, interaction evidence, and large-space
comparison are **not supported** here. The result documents how hard it was to recover
multi-component dependency-drift incidents under the stated reconstruction rules; it does
not measure algorithm performance or imply that such incidents do not exist.

## Noise-guarantee simulations (pre-registered, one run each)

These test the diagnosis-level bound of `interval: anytime`, whose proof is in
[VERIFICATION.md](VERIFICATION.md#diagnosis-level-error-control-interval-anytime). The
protocols ([v1](../benchmarks/noise_guarantee/PROTOCOL.md),
[v2](../benchmarks/noise_guarantee/PROTOCOL_V2.md)) and the library were hashed before each
run. Incidents are synthetic, with exactly known mask means, so every true minimal failing
set is known.

| study | scenarios | interval | wrong `verified` | investigations | correct `verified` |
|---|---|---|---:|---:|---:|
| v1 | 5 meeting the assumptions, `k` 4–8 | anytime | **0** | 36,000 | 24.7% |
| v1 | same | student_t | 0 | 36,000 | 28.4% |
| v1 | same | normal | 0 | 36,000 | 37.0% |
| v2 | stress near the threshold, `extended` audit | anytime | **0** | 3,600 | 0% (abstains) |
| v2 | same | student_t | **98** | 3,600 | 0% |
| v2 | same | normal | **149** | 3,600 | 0% |
| v2 | stress, audit off | anytime / student_t / normal | **0 / 210 / 503** | 3,600 each | |
| v2 | non-monotone masked healing, audit off | anytime / student_t / normal | **0 / 0 / 17** | 3,600 each | |

Version 1 could not tell the methods apart. Version 2 shows that per-comparison intervals
produce wrong `verified` results when a cause sits just above the threshold and a decoy
just below it. With the `extended` audit, every Student-t `verified` result in that
scenario was wrong. `anytime` held the bound by abstaining, at a cost: about 40% more runs
than Student-t in version 1, and in the stress scenario it never verified. When the
declared noise scale was three times too small, the safeguard flagged every incident and
withheld `verified`. Version 1's `healing` scenario was mis-specified (88% of its incidents
had no regression). Because of version 2, a noisy incident judged by Student-t now ends
at most `inferred`.

## Large-search-space study (pre-registered, synthetic)

[Protocol](../benchmarks/scale/PROTOCOL.md) and [report](../benchmarks/results/scale/REPORT.md).
`k` in {8, 10, 12} (256 to 4,096 states), 100 incidents per scenario and size, six strategies,
budgets 8 to the full space, deterministic oracle replays: 54,000 investigations. The
incidents satisfy the method's model by construction except the non-monotone control, so
this measures scaling and cost, not external validity.

- **Safety:** 0 wrong `verified` for single and pair causes and for the non-monotone
  masked-healing control. At budgets of 12 or more, the extended audit turned every
  adaptive run on the control into `assumption_violated`; at budget 8, 28–42% ended
  `assumption_violated` and the rest `inferred` or `unresolved` (no verified claim).
- **Engine cost at `k = 12`:** adaptive takes 0.37 s per investigation and at most 2.5 MB of
  traced memory (pre-registered limits: 2 s and 256 MB).
- **Pairs:** at `k = 12` and a budget of 16 isolation replays, adaptive verified 100% of
  pair causes, ddmin 41%, exhaustive 1%, one-factor-at-a-time 0%. At the full budget,
  adaptive needed fewer isolation replays than ddmin in 78–87 of 100 incidents per size
  (sign test p < 1e-8).
- **Single causes: ddmin is cheaper.** Delta debugging needed fewer isolation replays in
  42–60 of 100 incidents per size, adaptive in 5–10 (p < 1e-6). Adaptive also spends
  replays ruling out pair hypotheses (7.8 against 7.3 isolation replays at `k = 12`).
- **The audit dominates cost at scale.** For a single cause at `k = 12`, the `extended`
  audit added about 131 replays to 7–8 isolation replays, roughly 95% of the total. For
  pairs it added about 111. Making the audit risk-based or incremental is the main open
  cost problem (roadmap gate 3).

## Reproduce

```bash
pip install -e ".[demo,dev]"                    # plus pandas, pyarrow, huggingface_hub, Pillow for the holdout
python benchmarks/freeze_method.py verify       # frozen behavior unchanged
python benchmarks/seal.py verify benchmarks/holdout
python benchmarks/holdout/setup_envs.py && python benchmarks/holdout/prepare.py   # data and interpreters
python benchmarks/prove_ground_truth.py benchmarks/holdout
python benchmarks/reproduce_frozen.py --output /tmp/regressleuth-frozen-reproduction
python benchmarks/evaluate_safe_default.py     # writes only benchmarks/results/safe_default/
python benchmarks/drift/harness.py verify       # drift study: sealed ledger and method freeze
python3.11 benchmarks/historical/setup_envs.py  # matched historical environments (network)
regressleuth diagnose benchmarks/historical/incidents/sklearn-issue-35038/incident.yaml  # live replay
python benchmarks/historical/verify_snapshot.py  # pilot reproduced from the frozen source archive
python benchmarks/noise_guarantee/simulate.py smoke  # the pre-registered runs refuse to overwrite
python benchmarks/scale/scale.py smoke
regressleuth bench                              # synthetic suite
python docs/make_figures.py
```

The stored replay tables (`results/tables/`) let `evaluate.py` recompute every number without
rerunning models. Development text incidents need the Hugging Face models (`.[text-demo]`).
