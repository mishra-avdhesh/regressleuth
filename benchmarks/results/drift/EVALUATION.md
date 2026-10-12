# Dependency-drift suite (sealed, evaluated once)

Protocol: [SELECTION_PROTOCOL.md](../../drift/SELECTION_PROTOCOL.md) with addenda A and B.

## Funnel

- Logged: **40**; excluded: **33** (build_infeasible 16, download_too_large 1, no_fixed_test 13, not_dependency_drift 9, outside_population 1, search_space_above_cap 1)
- Replayed: **7**; disputed: **7** (nestcheck-pandas3-numpy246-12, seaborn-numpy231-3892, classeval-numpy2-pandas3-3, audformat-pandas302-527, partd-pandas3-82, scikit-mol-pandas-51, pypet-pandas220-72); included and sealed: **0** (none)

Why each replayed candidate was disputed (from its controlled replay):

- `nestcheck-pandas3-numpy246-12`: In the good state the test modules fail to import (NameError: name 'unittest' is not defined in tests/test_core.py), unrelated to the blamed pandas and NumPy, which did not change in the window. (Checked by rerunning the named tests in the endpoint environment before sealing.)
- `seaborn-numpy231-3892`: The good state (2025-11-30: NumPy 2.3.5, matplotlib 3.10.7) already fails the named tests with the reported errors (KeyError 'labelleft'; numpy.VisibleDeprecationWarning removed). The report describes a NumPy 1.26 to 2.3 upgrade that happened long before its 14-day fallback window. (Checked by rerunning the named tests in the endpoint environment before sealing.)
- `classeval-numpy2-pandas3-3`: The release's declared requirements (addendum B4) omit pandas, which its code imports, so both states fail at import (ModuleNotFoundError: pandas). The reported failure could not be tested under the rules. (Checked by rerunning the named tests in the endpoint environment before sealing.)
- `audformat-pandas302-527`: The good state (pandas 3.0.1) already fails test_load_old_pickle (dtype object, expected string), consistent with the maintainer's diagnosis that the test, not pandas 3.0.2, was at fault. (Checked by rerunning the named tests in the endpoint environment before sealing.)
- `partd-pandas3-82`: The good state (2026-02-06) already resolves pandas 3.0.0 and fails with the reported AttributeError: 'StringDtype' object has no attribute 'str'. The report came weeks after pandas 3.0. (Checked by rerunning the named tests in the endpoint environment before sealing.)
- `scikit-mol-pandas-51`: The bad state (2024-09-27) passes. The reported failure involved scikit-learn 1.2.2 and disappeared after a scikit-learn upgrade; it was not drift between these two dates. (Checked by rerunning the named tests in the endpoint environment before sealing.)
- `pypet-pandas220-72`: The good state (2024-02-07) already resolves pandas 2.2.0 and fails with the reported AttributeError: 'int' object has no attribute 'decode'. The report came a month after pandas 2.2.0. (Checked by rerunning the named tests in the endpoint environment before sealing.)

## Pre-registered decisions

- Search advantage: **not supported**: no included incident has three or more changed components, so the pre-registered paired comparison has no incidents to compare
- Interaction evidence: **not established** (incidents with a minimal cause of two or more components: none; verified correctly at full budget by at least one strategy: none)
- Large search spaces (k >= 8): 0 incident(s) with k >= 8 (none); described per incident, not summarized as a rate

## Outcomes per strategy (wrong verified first)

| strategy | budget | WRONG verified | correct verified | correct inferred | unresolved | inconclusive | assumption violated | errors | mean isolation | mean total | runs |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

## Per incident, full budget

| incident | k | stratum | cause sizes | coupled | strategy | status | diagnosis | isolation | total |
|---|---:|---|---|---|---|---|---|---:|---:|
