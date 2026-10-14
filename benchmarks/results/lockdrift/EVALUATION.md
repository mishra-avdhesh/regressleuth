# Lockfile-update suite (dependency drift v2; sealed, evaluated once)

Protocol: [SELECTION_PROTOCOL.md](../../lockdrift/SELECTION_PROTOCOL.md) and any dated addenda.

## Funnel

- Logged: **40**; excluded: **37** (build_infeasible 2, no_lockfile 8, no_test_command 2, not_dependency_drift 4, outside_population 4, python_unavailable 6, search_space_above_cap 14)
- Replayed: **3**; disputed: **3** (annuaire-entreprises-data-gouv-fr-search-inf-pr950, diogoribeiro7-drl-cox-pr60, diogoribeiro7-drl-cox-pr59); included and sealed: **0** (none)

Why each replayed candidate was disputed (from its controlled replay):

- `annuaire-entreprises-data-gouv-fr-search-inf-pr950`: No test passes in the good state and fails in the bad state.
- `diogoribeiro7-drl-cox-pr60`: No test passes in the good state and fails in the bad state.
- `diogoribeiro7-drl-cox-pr59`: No test passes in the good state and fails in the bad state.

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
