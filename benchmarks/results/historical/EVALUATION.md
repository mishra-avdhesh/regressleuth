# Historical external incident pilot

This evaluation is separate from the frozen development and holdout benchmarks.
It uses the sealed, source-derived observation tables; all six strategies share
the same observations, `extended` audit, and Student-t default. Results are
descriptive. A one-component incident has only two states and does not show a
search advantage.

Included incidents: 9. Full per-run data: `rows.json`.

Changed components per incident (cause-size strata are reported separately): 1: 9. Budgets above an incident's search space are marked in `rows.json`.

## Candidate funnel (all logged candidates)

- Logged before any reproduction: **30**
- Excluded by the predeclared eligibility rules: **21** duplicate_transition 4, infeasible_hybrids 2, no_bad_state 2, no_dated_public_regression 1, no_good_state 6, unfixed_test 3, uninstallable_dependency 3
- Sent to controlled reproduction: **9**
- Disputed (reproduction did not support the report; kept, excluded from accuracy): **0** 
- Included, independently reproduced and sealed: **9**
- Still unscreened: **0**

## Outcomes per strategy (wrong verified first)

| strategy | budget | WRONG verified | correct verified | correct inferred | unresolved | inconclusive | assumption violated | runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| adaptive | 4 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| adaptive | 6 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| adaptive | 8 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| adaptive | 12 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| adaptive | full | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| exhaustive | 4 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| exhaustive | 6 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| exhaustive | 8 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| exhaustive | 12 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| exhaustive | full | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| random | 4 | **0** | 90 | 0 | 0 | 0 | 0 | 90 |
| random | 6 | **0** | 90 | 0 | 0 | 0 | 0 | 90 |
| random | 8 | **0** | 90 | 0 | 0 | 0 | 0 | 90 |
| random | 12 | **0** | 90 | 0 | 0 | 0 | 0 | 90 |
| random | full | **0** | 90 | 0 | 0 | 0 | 0 | 90 |
| one_factor | 4 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| one_factor | 6 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| one_factor | 8 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| one_factor | 12 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| one_factor | full | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| greedy | 4 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| greedy | 6 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| greedy | 8 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| greedy | 12 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| greedy | full | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| ddmin | 4 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| ddmin | 6 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| ddmin | 8 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| ddmin | 12 | **0** | 9 | 0 | 0 | 0 | 0 | 9 |
| ddmin | full | **0** | 9 | 0 | 0 | 0 | 0 | 9 |

Total wrong `verified` diagnoses across all strategy-budget-seed runs: **0**.

## All metrics

| strategy | budget | incidents | runs | correct verified | false verified | correct inferred | unresolved | inconclusive | assumption violated | mean isolation | mean audit | mean total | mean replay wall s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| adaptive | 4 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| adaptive | 6 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| adaptive | 8 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| adaptive | 12 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| adaptive | full | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| exhaustive | 4 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| exhaustive | 6 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| exhaustive | 8 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| exhaustive | 12 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| exhaustive | full | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| random | 4 | 9 | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| random | 6 | 9 | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| random | 8 | 9 | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| random | 12 | 9 | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| random | full | 9 | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| one_factor | 4 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| one_factor | 6 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| one_factor | 8 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| one_factor | 12 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| one_factor | full | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| greedy | 4 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| greedy | 6 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| greedy | 8 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| greedy | 12 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| greedy | full | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| ddmin | 4 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| ddmin | 6 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| ddmin | 8 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| ddmin | 12 | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |
| ddmin | full | 9 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 2.00 | 0.00 | 2.00 | 1.107 |

## Per-incident full-budget results

| incident | components | space | strategy | status | diagnosis | false verified | total replays | replay wall s |
|---|---:|---:|---|---|---|---:|---:|---:|
| pandas-attrs-deepcopy-57859 | 1 | 2 | adaptive | verified | ['pandas'] | 0 | 2 | 0.835 |
| pandas-attrs-deepcopy-57859 | 1 | 2 | exhaustive | verified | ['pandas'] | 0 | 2 | 0.835 |
| pandas-attrs-deepcopy-57859 | 1 | 2 | random | verified | ['pandas'] | 0 | 2 | 0.835 |
| pandas-attrs-deepcopy-57859 | 1 | 2 | one_factor | verified | ['pandas'] | 0 | 2 | 0.835 |
| pandas-attrs-deepcopy-57859 | 1 | 2 | greedy | verified | ['pandas'] | 0 | 2 | 0.835 |
| pandas-attrs-deepcopy-57859 | 1 | 2 | ddmin | verified | ['pandas'] | 0 | 2 | 0.835 |
| pandas-groupby-nan-63920 | 1 | 2 | adaptive | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-groupby-nan-63920 | 1 | 2 | exhaustive | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-groupby-nan-63920 | 1 | 2 | random | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-groupby-nan-63920 | 1 | 2 | one_factor | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-groupby-nan-63920 | 1 | 2 | greedy | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-groupby-nan-63920 | 1 | 2 | ddmin | verified | ['pandas'] | 0 | 2 | 0.938 |
| sklearn-linear-float32-33032 | 1 | 2 | adaptive | verified | ['scikit-learn'] | 0 | 2 | 1.651 |
| sklearn-linear-float32-33032 | 1 | 2 | exhaustive | verified | ['scikit-learn'] | 0 | 2 | 1.651 |
| sklearn-linear-float32-33032 | 1 | 2 | random | verified | ['scikit-learn'] | 0 | 2 | 1.651 |
| sklearn-linear-float32-33032 | 1 | 2 | one_factor | verified | ['scikit-learn'] | 0 | 2 | 1.651 |
| sklearn-linear-float32-33032 | 1 | 2 | greedy | verified | ['scikit-learn'] | 0 | 2 | 1.651 |
| sklearn-linear-float32-33032 | 1 | 2 | ddmin | verified | ['scikit-learn'] | 0 | 2 | 1.651 |
| moneyprinter-pillow-antialias-70 | 1 | 2 | adaptive | verified | ['pillow'] | 0 | 2 | 0.234 |
| moneyprinter-pillow-antialias-70 | 1 | 2 | exhaustive | verified | ['pillow'] | 0 | 2 | 0.234 |
| moneyprinter-pillow-antialias-70 | 1 | 2 | random | verified | ['pillow'] | 0 | 2 | 0.234 |
| moneyprinter-pillow-antialias-70 | 1 | 2 | one_factor | verified | ['pillow'] | 0 | 2 | 0.234 |
| moneyprinter-pillow-antialias-70 | 1 | 2 | greedy | verified | ['pillow'] | 0 | 2 | 0.234 |
| moneyprinter-pillow-antialias-70 | 1 | 2 | ddmin | verified | ['pillow'] | 0 | 2 | 0.234 |
| pandas-issue-63304 | 1 | 2 | adaptive | verified | ['pandas'] | 0 | 2 | 0.988 |
| pandas-issue-63304 | 1 | 2 | exhaustive | verified | ['pandas'] | 0 | 2 | 0.988 |
| pandas-issue-63304 | 1 | 2 | random | verified | ['pandas'] | 0 | 2 | 0.988 |
| pandas-issue-63304 | 1 | 2 | one_factor | verified | ['pandas'] | 0 | 2 | 0.988 |
| pandas-issue-63304 | 1 | 2 | greedy | verified | ['pandas'] | 0 | 2 | 0.988 |
| pandas-issue-63304 | 1 | 2 | ddmin | verified | ['pandas'] | 0 | 2 | 0.988 |
| pandas-issue-65118 | 1 | 2 | adaptive | verified | ['pandas'] | 0 | 2 | 0.937 |
| pandas-issue-65118 | 1 | 2 | exhaustive | verified | ['pandas'] | 0 | 2 | 0.937 |
| pandas-issue-65118 | 1 | 2 | random | verified | ['pandas'] | 0 | 2 | 0.937 |
| pandas-issue-65118 | 1 | 2 | one_factor | verified | ['pandas'] | 0 | 2 | 0.937 |
| pandas-issue-65118 | 1 | 2 | greedy | verified | ['pandas'] | 0 | 2 | 0.937 |
| pandas-issue-65118 | 1 | 2 | ddmin | verified | ['pandas'] | 0 | 2 | 0.937 |
| pandas-issue-66341 | 1 | 2 | adaptive | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-issue-66341 | 1 | 2 | exhaustive | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-issue-66341 | 1 | 2 | random | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-issue-66341 | 1 | 2 | one_factor | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-issue-66341 | 1 | 2 | greedy | verified | ['pandas'] | 0 | 2 | 0.938 |
| pandas-issue-66341 | 1 | 2 | ddmin | verified | ['pandas'] | 0 | 2 | 0.938 |
| sklearn-issue-34883 | 1 | 2 | adaptive | verified | ['scikit-learn'] | 0 | 2 | 1.796 |
| sklearn-issue-34883 | 1 | 2 | exhaustive | verified | ['scikit-learn'] | 0 | 2 | 1.796 |
| sklearn-issue-34883 | 1 | 2 | random | verified | ['scikit-learn'] | 0 | 2 | 1.796 |
| sklearn-issue-34883 | 1 | 2 | one_factor | verified | ['scikit-learn'] | 0 | 2 | 1.796 |
| sklearn-issue-34883 | 1 | 2 | greedy | verified | ['scikit-learn'] | 0 | 2 | 1.796 |
| sklearn-issue-34883 | 1 | 2 | ddmin | verified | ['scikit-learn'] | 0 | 2 | 1.796 |
| sklearn-issue-35038 | 1 | 2 | adaptive | verified | ['scikit-learn'] | 0 | 2 | 1.647 |
| sklearn-issue-35038 | 1 | 2 | exhaustive | verified | ['scikit-learn'] | 0 | 2 | 1.647 |
| sklearn-issue-35038 | 1 | 2 | random | verified | ['scikit-learn'] | 0 | 2 | 1.647 |
| sklearn-issue-35038 | 1 | 2 | one_factor | verified | ['scikit-learn'] | 0 | 2 | 1.647 |
| sklearn-issue-35038 | 1 | 2 | greedy | verified | ['scikit-learn'] | 0 | 2 | 1.647 |
| sklearn-issue-35038 | 1 | 2 | ddmin | verified | ['scikit-learn'] | 0 | 2 | 1.647 |

The displayed 0.95 Student-t setting, where applied, is an interval setting for
individual replay comparisons. It is not a confidence bound for the diagnosis.
