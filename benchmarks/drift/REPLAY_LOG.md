# Replay harness log

Times are IST on 2026-10-11. The ledger, tests and thresholds were not changed by anything
below. Only the replay harness changed, and every candidate was then replayed again under
the final harness.

1. **01:21–01:28.** First replay of `seaborn-numpy231-3892`. The good state (2025-11-30
   resolution) failed the three named tests with the reported errors, so the candidate was
   marked disputed.
2. **About 01:47. Contamination.** A code formatter (`ruff format benchmarks/drift`) also
   rewrote files under `work/`: 670 extracted project-source files and 5,798 Python files in
   the uv package cache. Virtual environments link to that cache. The rewrites were
   formatting only, but replays must use the released artifacts byte for byte. The partd
   replay running at the time was stopped before it wrote anything. `work/sources`,
   `work/envs`, `work/uv-cache` and the built wheels were deleted and rebuilt from the
   untouched downloaded tarballs and fresh wheel downloads. Since then:
   - ruff excludes `benchmarks/drift/work` and `benchmarks/historical/envs`;
   - the runner checks every installed file against its wheel's RECORD hashes before use;
   - `drift.py replay` checks the extracted project tree against the tarball, file for file.

   The historical pilot's environments were checked the same way: 62,986 recorded files,
   with 12 mismatches, all compiled `.pyc` caches.
3. **01:49–01:52.** After the rebuild, seaborn was replayed again with the same result
   (good state fails), and its resolution files were byte-identical.
4. **01:52–01:55. Harness error, not a finding.** Both partd endpoints ended as runner
   errors. pandas 3 looks up `US/Central`, and this machine's time-zone database (Ubuntu
   24.04) lacks the legacy names, which now ship in a separate package; partd's CI used
   conda-forge, whose database has them. The replay script had wrongly marked the
   candidate disputed. Fixes:
   - every replay now receives a fixed, complete IANA database (`tzdata==2025.2`, via
     `PYTHONTZPATH`, as a host with a full system database would provide);
   - a test module that cannot be collected under a mix counts as a failed test (metric 0)
     rather than a runner error;
   - an endpoint replay error now leaves the candidate pending instead of disputing it.

   Earlier replay tables were removed, and all seven remaining candidates, including
   seaborn and partd, were replayed from scratch under this harness. From then on, each
   attempt is appended to the incident's `replay_attempts.jsonl`.
5. **02:08. Stopped on request.** The replay of pypet was interrupted. Two endpoint errors
   from that run turned out to be harness faults, and both candidates stayed pending:
   - scikit-mol: a virtual environment left unfinished by an earlier interrupted build
     blocked its re-creation. The runner now discards an environment without its completion
     marker and builds it again.
   - audformat (2026): the new RECORD check reported files under `docs/` that several
     audeering wheels all install at the same top-level path; whichever installs last wins.
     The check now accepts a file whose content matches any RECORD entry for that path
     (a collision) and fails only on content that matches none (tampering).

   scikit-mol, audformat (2026) and pypet were then replayed under the corrected runner.
