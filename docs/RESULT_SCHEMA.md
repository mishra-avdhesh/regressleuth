# Result schema 1.0 and exit codes

`regressleuth diagnose --format json` writes one JSON object
([`result-1.0.schema.json`](../src/regressleuth/schemas/result-1.0.schema.json),
`regressleuth schema result`). Text, Markdown and HTML reports are rendered from it, and
`regressleuth report RESULT.json --format html` re-renders a saved result.

| Field | Meaning |
|---|---|
| `schema`, `schema_version` | `"regressleuth.result"`, `"1.0"` |
| `tool` | name and version that produced the result |
| `incident` | id, spec version, changed and unchanged components, good/bad versions (per `report.values` policy), metric |
| `search` | strategy, seed, `max_cause_size`, `hypothesis_count` (candidate causes considered), `search_space` (2^k, the full exhaustive replay count), audit level |
| `status` | one of the statuses below (never collapsed) |
| `diagnosis` | the cause (list of components) for `verified` and `inferred`, else `null` |
| `suspected_cause` | what a contradicted audit was about to report (`assumption_violated` only) |
| `reason` | one sentence explaining the status |
| `alternatives` | candidate causes still compatible with every definite observation |
| `replays` | `budget`, `isolation_used` (endpoints + search + verification), `audit_used`, `total`, `runner_runs` (with repeats) |
| `confidence` | interval type and level, repeats, max repeats |
| `verification` | effective audit mode, interval method and whether used, confidence, repeats/max repeats, status of every assumption check, and verification scope |
| `assumptions` | each assumption with status `checked`, `partially_checked`, `not_checked`, `violated`, `handled` or `assumed` |
| `audit` | required and confirmed audit checks, violations (expected vs observed) |
| `experiments` | every replay in order: components set to bad, outcome, mean metric, sd, runs, role, candidate causes remaining after it, error kind |
| `errors` | counts of incompatible, error and inconclusive replays, and error kinds |
| `runtime_seconds`, `adapter` | wall time; adapter type and reproducibility metadata (never secret values or local absolute paths) |

## Statuses and exit codes

| Status | Meaning | Exit code |
|---|---|---:|
| `verified` | verified under the configured replay model, assumptions, and audit checks ([details](VERIFICATION.md)); this is a bounded replay result, not unrestricted causal proof | 0 |
| `inferred` | a unique compatible cause, but minimality or audit checks could not all run | 2 |
| `inconclusive` | noise left the decisive replays undecided (or the endpoints inseparable) | 2 |
| `unresolved` | budget or strategy exhausted with several compatible causes | 2 |
| `invalid_baseline` | the bad state does not regress on these cases and threshold | 2 |
| `assumption_violated` | observations contradict a monotone cause of at most `max_cause_size` components; no cause is reported | 5 |
| `evaluation_error` | a replay crashed, timed out or returned malformed output | 4 |
| (invalid incident, arguments or result file) | `validate`, `inspect`, `diagnose`, `report` refuse | 3 |

Exit codes are stable across 0.x. Code 2 groups outcomes without verification. Exit code 0
means the configured verification checks passed; it does not establish unrestricted causality.

Compatibility: `schema_version` "1.0" is frozen like the incident specification; fields may
be added in 1.x, never removed or redefined.
