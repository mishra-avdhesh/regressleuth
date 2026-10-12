# Noise-guarantee simulation, version 2 (separate pre-registration)

**Written and frozen before its run** (2026-10-11 IST), after the version 1 run. Version 1
and its results are unchanged. `FREEZE_V2.json` hashes this file, `simulate_v2.py`,
`simulate.py` (reused helpers) and `src/regressleuth`.

## Why a second study

Version 1 supported the claim (0 wrong `verified` with `anytime`), but it had two
weaknesses that are visible in its results. First, it could not discriminate: `student_t`
and `normal` also had 0 wrong `verified`, so it did not show when the bound matters.
Second, its `healing` scenario was mis-specified. The healing change was also present in
the known-bad state, so 88% of those incidents had no regression (`invalid_baseline`).
Version 2 targets both without changing the method or version 1.

## Design

Same claim, assumptions and definitions as version 1. Changes:

- `masked_healing` (non-monotone, assumptions hold): cause `C` (one or two components),
  healer `h` and guard `g`, all distinct. A mask fails iff `C` is bad and not (`h` bad and
  `g` good). The known-bad state fails, while `C + h` passes.
- `stress_near` (assumptions hold): one cause with drop U[1.0, 1.1] x threshold, one decoy
  component with effect U[0.85, 0.99] x threshold, the others 0; noise SD 0.5 x threshold.
- Audit `extended` and audit `0` (off). The theorem does not use the audit; with it off,
  only the interval protects against a wrong `verified`.
- Repeats 2, max_repeats 40 (many looks), `k` in {4, 6, 8}, sigma 0.5 x threshold, the six
  strategies, intervals `anytime`, `student_t`, `normal`, full budget, confidence 0.95,
  200 incidents per (scenario, k) cell, paired noise as in version 1.

## Decision rule

Primary: for `anytime`, per (scenario, audit) pooled over `k` (600 investigations per
strategy), every observed wrong-`verified` rate is at most 0.05 and every one-sided 95%
Clopper-Pearson upper bound is at most 0.05. Secondary, without a rule: the same rates
for `student_t` and `normal`, correct verified rates and mean runs.

Nothing is changed after the run; failures are reported as found.
