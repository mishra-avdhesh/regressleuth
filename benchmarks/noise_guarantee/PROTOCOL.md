# Noise-guarantee simulation protocol

**Written and frozen before the main run** (2026-10-11 IST). `FREEZE.json` records the
SHA-256 of this file, `simulate.py` and every file in `src/regressleuth`; `simulate.py run`
refuses to start if any of them changed, and refuses to overwrite existing results.
Before freezing, only a smoke run was made: 1 incident per cell, seeds disjoint from the
main run, and it printed only how many investigations completed, not their outcomes.

## Claim under test

With `interval: anytime`, confidence `1 - alpha`, and a declared `noise_scale` sigma, the
following holds for any strategy, budget, audit setting and stopping behaviour
(docs/VERIFICATION.md gives the proof):

> P(status is `verified` and the reported set is not a minimal failing set of the true
> mask means) <= alpha,

provided that (A1) each mask has a fixed true mean, (A2) runs are independent given the
mask, and (A3) each run's noise is sigma-sub-Gaussian. A *minimal failing set* is a set
of changed components whose mask fails (true effect at least the threshold) while every
non-empty proper subset passes. No monotonicity is assumed.

## Design

Every incident is synthetic, with an exactly known mean for each of the `2^k` masks, so the
true minimal failing sets are computed exhaustively.

- Changed components `k` in {4, 6, 8}; threshold 0.02 on a higher-is-better metric with
  base 0.9; declared sigma in {0.25, 0.5} x threshold.
- Each incident runs with `interval` in {anytime, student_t, normal}, and with each of the
  six strategies, at the full budget `2^k`, `extended` audit, causes of at most two
  components, repeats 3, max_repeats 24, confidence 0.95. Every combination of interval
  and strategy reads the same noise draw for the same mask and run index (paired design).
- 200 incidents per (scenario, k, sigma) cell; the incident seed defines everything.

Scenarios (benign effects are independent per component; `U` is uniform):

| scenario | assumptions | true means |
|---|---|---|
| `single` | hold | one cause component, drop U[1.5, 4] x threshold; other components U[-0.1, 0.1] x threshold each |
| `pair` | hold | the drop applies only when both members of a random pair are bad |
| `near_threshold` | hold | single or pair cause with drop U[1.05, 1.3] x threshold; benign effects U[0, 0.12] x threshold each, pushing passing masks toward the threshold |
| `healing` | hold (non-monotone) | single or pair cause; a further component cancels the drop when bad |
| `two_causes` | hold (non-unique) | two disjoint causes (each single or pair), either one fails |
| `misdeclared` | A3 violated | as `single`/`pair` alternately, true noise SD 3 x the declared sigma |
| `heavy_tail` | A3 violated | as `single`/`pair` alternately, Student-t noise with 3 degrees of freedom scaled to SD sigma |

## Outcomes and decision rule

Primary: for `anytime`, the wrong-verified rate per strategy, pooled over the five
assumption-holding scenarios (6,000 investigations per strategy), and per scenario for
`adaptive`. The claim is supported if every such observed rate is at most 0.05 and every
one-sided 95% Clopper-Pearson upper bound is at most 0.05. Otherwise the claim is reported
as not supported, with the failing cells.

Secondary, reported without a pass/fail rule: the same rates for `student_t` and `normal`;
correct verified rate (power), inferred, inconclusive, unresolved and assumption-violated
rates; mean runs per investigation; and all rates in the two violation scenarios, including
how often the declared-noise safeguard withheld `verified`.

No setting in this protocol or in the library is changed after the main run. A failure is
reported, not repaired.
