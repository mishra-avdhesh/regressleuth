# Candidate search record (lockfile-update incidents)

Search dates: 2026-10-12/13 UTC. Queries use the public GitHub issue-search API (pull
requests, newest first, 30 per page) and are listed in the order they were run. A result is
a **candidate** when it is a Dependabot or Renovate pull request that changes a lockfile and
failed a CI check (the query enforces both). Population membership, the transition and
the CI test job are checked by `study.py screen`. Candidates are logged in listed order in
`CANDIDATES.jsonl`, exclusions included.

## Queries

1. `is:pr author:app/dependabot status:failure "uv.lock" pandas created:<2026-10-12`: 505 hits.
2. `is:pr author:app/dependabot status:failure "poetry.lock" numpy created:<2026-10-12`: 197 hits.
   Run together with query 1, before any screening. Results are examined only after query
   1's page is exhausted.

All 30 results of query 1 were candidates by construction (bot pull requests that change a
lockfile and failed a check), logged in listed order. Query 2 then supplied the next 10 in
listed order, which reached the intake cap.

`study.py screen` changed twice during screening; neither change altered a rule. First,
it now detects human commits on top of the bot's commit (MSKazemi/novafabric#146 had
been read with a wrong base). Second, `requirements*.in` files count as requirement files,
as the protocol states. Every query-1 candidate was then screened again with the
corrected tool.

**Intake closed: 40 logged candidates (35 excluded, 5 eligible for replay).**
