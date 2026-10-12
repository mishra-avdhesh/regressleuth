# Candidate search record

Search dates: 2026-10-10/11 UTC. Searches use the public GitHub issue-search API (sorted by
creation date, newest first, 30 results) and are listed in the order they were run.
A result is a **candidate** when its title or body reports a test or CI failure in a
Python project, attributed to a dependency. Candidates are screened in listed order and
logged in `CANDIDATES.jsonl`, including exclusions. Results that are not candidates by that
definition are listed per query, so the filter can be audited.

## Queries

1. `is:issue language:python "new release" "tests" "failing" numpy`: 894 hits. No result
   on the first page was a candidate (agent coordination boards, CI dashboards, feature
   epics).
2. `is:issue "CI is failing" "nothing changed" scikit-learn`: 3 hits, none a candidate.
3. `is:issue "tests started failing" pandas`: 87 hits. Candidates are logged from this page
   in listed order. Not candidates: ContextLab/orchestrator#124 (API keys in CI),
   jiridanek/rhoai-in-kind#38 (test-suite version, not a dependency release),
   TileDB-Inc/centralized-tiledb-nightlies#18 (a nightly job report with no dependency
   named), pola-rs/polars#20003, #18393 and #16435 (bugs in the library itself, not
   dependency-caused), sfu-db/connector-x#811 (a timezone bug), and lakehq/sail#538 (a
   parity bug).

   Examined but not candidates (addendum B5): pandas-dev/pandas#57511 (no dependency
   blamed), sandialabs/OpenCSP#198 (no dependency blamed), alkaline-ml/pmdarima#582 (an
   installation failure, not a test failure). The 19 candidates from this page are logged in
   listed order (newest first).
4. `is:issue "tests fail" "new release of" numpy OR pandas OR scipy OR scikit-learn created:<2026-10-10`:
   5,769 hits; the first page held no candidates (the `OR` terms matched unrelated
   project-management issues).
5. `is:issue "CI" "broken by" release pandas OR numpy OR scipy OR scikit-learn OR pyarrow created:<2026-10-10`:
   12,999 hits; no candidates on the first page, for the same reason.
6. `is:issue in:title "tests fail with" pandas created:<2026-10-10`: 38 hits. Candidates
   were logged in listed order until the intake cap of 40 was reached at
   scverse/anndata#709. Examined but not candidates (addendum B5): NVIDIA/cudf#20424 and
   #17934 (cuDF's own behaviour, no dependency blamed), epic-framework/epic-pandas#1 (a
   naming collision, no dependency blamed). IBM/nzpyida#20 reports the same transition as
   #21 and is recorded as a second source of that candidate.
7. `is:issue in:title "test failures with" numpy created:<2026-10-10` and
8. `is:issue in:title "tests fail with" scipy created:<2026-10-10` were run before the cap
   was reached, but none of their results was examined, because the cap filled from
   query 6.

**Intake closed: 40 logged candidates.**
