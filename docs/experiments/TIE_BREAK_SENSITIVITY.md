# Component-name tie-break sensitivity

The adaptive search uses a lexical tie-break when several replay masks have equal
predicted information gain. The holdout has five changed components per incident,
so a small budget can make this naming choice visible in the result.

`python3 benchmarks/analysis/tie_break_sensitivity.py` tests this without
rerunning models or changing the sealed suite. For each of the seven holdout
incidents, it assigns the same five neutral names to the changed components in
all `5! = 120` ways. It renames the stored replay-table keys and declared cause
accordingly, then runs adaptive and ddmin with budget 8, cause size 2, and the
frozen `full` audit. Each strategy sees the same observations and noise values
as in the published evaluation. A success requires an exact, `verified` cause.

| Incident | Adaptive / 120 | ddmin / 120 |
|---|---:|---:|
| `holdout_csv_na_country_code` | 84 | 36 |
| `holdout_encoder_refit_per_batch` | 84 | 36 |
| `holdout_numpy2_float32_time` | 84 | 36 |
| `holdout_pandas3_datetime_epoch` | 120 | 120 |
| `holdout_proba_column_order` | 84 | 36 |
| `holdout_pythonhashseed_hashing` | 120 | 120 |
| `holdout_timezone_hour_feature` | 84 | 36 |
| **All 840 incident-permutations** | **660 (78.6%)** | **420 (50.0%)** |

With the original names, the corresponding counts are 6/7 (85.7%) and 4/7
(57.1%). The pairwise difference remains 28.6 percentage points under uniform
renaming, but the incident-level outcomes at budget 8 depend on the arbitrary
name order. The permutation results are a sensitivity analysis of the same seven
incidents, **not** 840 independent benchmark incidents or a new holdout. They do
not address the author-constructed incident selection or the validity of the
monotone cause assumption.
