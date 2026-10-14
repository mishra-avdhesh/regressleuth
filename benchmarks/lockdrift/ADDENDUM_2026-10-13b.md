# Addendum D, 2026-10-13 (IST), to the lockfile-update protocol

Written after addendum C, when the rebuilt endpoint environments were installed. Again,
**no test had run in any environment.**

1. **A second reader defect, fixed.** In `poetry.lock` 2.x a `markers` table lists only
   the dependency groups that need a marker; a package also belonging to another group is
   installed unconditionally for that group. The reader applied the table's markers alone,
   so colorama (Windows-only in `main` and `dev`, unconditional in `docs` via
   mkdocs-material) was left out, and `uv pip check` rejected the drl-cox endpoints. The
   reader now treats a group missing from the table as unconditional.
   `FREEZE_MANIFEST.v1.json` keeps the hashes of addendum C; `FREEZE_MANIFEST.json` was
   regenerated. The component counts of all seven candidates read from `poetry.lock` were
   recomputed. None changed (drl-cox #59: 4, #60: 6, redbox: 2; the excluded ones
   unchanged).
2. **CI checkout layout.** "The CI test job's pytest selection" runs in the directory
   layout CI uses. search-infra's CI checks the repository out as
   `data_pipelines_annuaire`, and its tests import the project under that name, so its
   source is placed in a directory of that name (`checkout_dir` in its record).
3. **Applying an existing rule.** market_research_AI_agent#24 pins `torch==2.14.0+cpu`
   from PyTorch's own package index. The runner installs from PyPI, so the endpoint
   environment cannot be built, and the candidate is excluded as `build_infeasible`
   under the rule as written.
