# What does `verified` mean?

`verified` means **verified under the configured replay model, assumptions, and audit checks**.
It is a bounded result about the replayed states and metric, not unrestricted causal proof.

## Definition

For an incident with changed components `C`, threshold `t`, and the set `S` of components
reported as the cause, `verified` means **all** of the following were observed on the
incident's fixed cases:

1. **The incident is real.** The all-good state passes and the all-bad state fails
   (its metric is worse by at least `t`; with noise, the confidence interval of the
   difference lies beyond `t`).
2. **Sufficiency.** The hybrid with only `S` set to bad fails.
3. **Minimality.** Every non-empty proper subset of `S` set to bad passes.
4. **Uniqueness under the model.** Every replay with a definite pass/fail outcome is
   consistent with `S` and with no other candidate cause of at most `max_cause_size`
   components.
5. **Audit.** The monotonicity audit at the configured level found no contradiction and
   every audit replay was conclusive:
   - `full` (historical benchmark profile): removing any member of `S` from the all-bad state passes, and adding
     any one other changed component to `S` still fails;
   - `extended` (new public default): additionally, adding any two other components to `S` still fails,
     and every single other component and every pair of other components passes on its own.

If 1 fails the status is `invalid_baseline` or `inconclusive`; if 2-3 cannot all be run it is
`inferred`; if 4 or 5 is contradicted it is `assumption_violated` and no cause is reported;
if 5 is incomplete (budget, incompatible hybrids, noise) it is `inferred`.

## Under which assumptions is verification valid?

`verified` is a statement about the replays that were run, interpreted under these
assumptions. The report lists each one with whether it was checked.

| Assumption | Checked? |
|---|---|
| A1. Every replay scores the same labeled cases with the same metric | No. The adapter or runner must guarantee it |
| A2. A replay depends only on the declared component versions and the run seed | No. Undeclared drift breaks attribution |
| A3. The regression has one minimal cause of at most `max_cause_size` components | Partly: contradictions are detected when replays expose them |
| A4. Monotonicity: with the cause present, adding bad components keeps the failure; without it, the bad components do not fail | Partly, by the audit (only the combinations listed above) |
| A5. Replays are deterministic, or their noise is captured by `repeats` and the interval | With `interval: anytime`, a declared `noise_scale` gives a diagnosis-level bound, and gross misdeclaration is detected; with Student-t, noisy results stop at `inferred` |
| A6. Incompatible hybrids are reported by the adapter, not silently mis-built | No |

## What `verified` does not mean

- It is **not causal proof** and not a guarantee about combinations that were never replayed.
- It does **not** guarantee that there is no *other*, latent failure elsewhere in the release.
  The historical `full` audit only probes near the candidate. On the bundled controls, a
  failing pair healed by another change in the same release, a pair of changes that cancel,
  and a failure healed only by two other changes together were all **verified** under the
  historical audit by adaptive, ddmin, greedy and one-factor search (exhaustive enumeration
  catches them). On the two non-monotone real-model controls this happened in 31 of their 60
  strategy-by-budget runs (and in 0 of 90 runs on the three other real controls). The diagnosed component is the one that fixes the deployed state, but the monotone
  model is false. The `extended` audit detected every one of these cases in our
  benchmarks, at the cost of roughly twice as many total replays. See
  [`benchmarks/results/evaluation/EVALUATION.md`](../benchmarks/results/evaluation/EVALUATION.md).
- With the historical **normal** interval and only 2 to 5 repeats, the interval is too narrow
  (the normal approximation ignores the uncertainty of the variance estimate), so an unlucky
  baseline can produce a spurious `fail`. New specification 1.0 incidents and the Python API
  use `replay.interval: student_t` (Welch's t) by default; more repeats are still needed for noisy metrics.
- The configured `confidence` is the nominal level of an interval for one metric comparison,
  not a confidence level for the final diagnosis. Noisy replays can be classified after
  several repeat counts, and search and audit compare multiple adaptively chosen masks.
  Reusing the same good baseline also links those comparisons. The current intervals do not
  adjust for optional stopping or multiple comparisons, so `confidence: 0.95` does not
  establish a 5% bound on the chance of an incorrect `verified` result. The `student_t`
  default improves small-sample intervals but does not remove this limitation. Since
  2026-10-11 a noisy incident judged by Student-t intervals therefore ends at most
  `inferred`. The `interval: anytime` mode below bounds the diagnosis-level error and can
  return `verified`.
- Causes of more than `max_cause_size` components are never verified; with the default 2,
  a three-way interaction ends as `assumption_violated` (never a wrong `verified` in our
  benchmarks). `max_cause_size: 3` searches triples at a higher replay cost.

**Practical reading:** the named components reproduce the regression on the fixed cases,
their tested proper subsets do not, and the configured audit found no contradiction.
The default `extended` audit still cannot cover every combination; full enumeration is
needed to rule out untested non-monotone combinations within the declared components.

## Diagnosis-level error control: `interval: anytime`

`replay.interval: anytime` with a declared `replay.noise_scale` (sigma) replaces the
per-comparison interval by **anytime-valid confidence sequences**, one per mask mean. With
`confidence: 1 - alpha` and `k` changed components:

**Guarantee.** Assume (A1) each mask has a fixed true mean metric, (A2) runs of a mask are
independent, and (A3) each run's noise is sigma-sub-Gaussian (Gaussian noise with standard
deviation at most sigma qualifies). Then, for every strategy, budget, audit setting, and
data-dependent stopping rule,

> P(status is `verified` and the reported set is **not** a minimal failing set) <= alpha,

where a *minimal failing set* is a set of components whose mask truly fails (true effect at
least the threshold) while every non-empty proper subset truly passes. No monotonicity is
assumed for this statement.

**Proof.** For mask `m` after `n` runs with mean `x_n`, the radius
`r(n) = sigma * sqrt(2 (n + 1) log(sqrt(n + 1) / a)) / n` satisfies
P(there is an `n` with `|x_n - mu_m| > r(n)`) <= `a`. This is Robbins' normal mixture: for
sigma-sub-Gaussian increments, `exp(l S_n - l^2 sigma^2 n / 2)` is a nonnegative
supermartingale for every `l`; mixing over `l ~ N(0, 1/sigma^2)` keeps that property and
gives `sqrt(1/(n+1)) exp(S_n^2 / (2 sigma^2 (n+1)))`, and Ville's inequality bounds its
ever reaching `1/a` by `a`. The engine uses `a = alpha / 2^k` for each of the `2^k` masks,
so by the union bound the event E that every mask's sequence covers its mean at every `n`
has probability at least `1 - alpha`. That covers every mask the search might choose, and
every stopping time, because each sequence is valid simultaneously over all `n`. A mask is
classified `fail` only when the lower end of `[x_0 - x_m] +- (r_0 + r_m)` (signed by the
metric direction) is at least the threshold, and `pass` only when its upper end is below the
threshold. On E, every `fail` and every `pass` therefore matches the true means (up to the
1e-12 floating-point tolerance used at the threshold).
`verified` requires that the reported set `D` was observed `fail` and every non-empty
proper subset of `D` was observed `pass`. On E those observations are true, so `D` is a
minimal failing set. Hence a wrong `verified` requires the complement of E, whose
probability is at most alpha. ∎

**What it does not say.** It does not say `D` is the *only* minimal failing set. That is
the monotone single-cause model, which the audit tests but cannot prove. It also does not
cover `inferred` results. The bound depends on sigma: if the true noise is larger, the
guarantee does not hold. As a safeguard that can only downgrade a result, `verified` is
withheld (`inferred`) when the pooled within-mask SD exceeds 2 x sigma with at least four
degrees of freedom, or shows any variation when sigma is 0. Heavy-tailed noise
(not sub-Gaussian) is outside the assumptions.

**Measured (pre-registered, one run each).**
[Version 1](../benchmarks/results/noise_guarantee/REPORT.md) covered five scenarios that
satisfy the assumptions (single, pair, near-threshold, non-monotone, two causes; `k` from 4
to 8). It had **0 wrong `verified` in 36,000 `anytime` investigations** (one-sided 95% upper
bound 0.0005 per strategy). Student-t and the normal interval also had 0 there, so
version 1 could not show when the bound matters. [Version 2](../benchmarks/results/noise_guarantee_v2/REPORT.md)
added a stress scenario: a cause just above the threshold, a decoy just below it, and many
looks. With the `extended` audit, Student-t produced **98 wrong `verified` in 3,600
investigations** (about 3% per strategy), and every Student-t `verified` result in that
scenario was wrong. The normal interval produced 149 (4%). With the audit off, the counts
were 210 and 503. `anytime` produced **0 in 7,200** with the audit on and off, because it
abstained instead. Version 1's `healing` scenario was mis-specified (the healing change was
present in the known-bad state, so 88% of incidents had no regression); version 2 replaced
it.

**Cost.** The error budget is split over `2^k` masks, so intervals are wider than the
default Welch interval and more runs are needed: the good baseline gets all `max_repeats`
runs at once, because every comparison shares it. The pre-registered simulation in
[`benchmarks/noise_guarantee/`](../benchmarks/noise_guarantee/PROTOCOL.md) measures the
error rate and the cost.

```yaml
replay:
  interval: anytime
  noise_scale: 0.004     # upper bound on one run's noise SD, e.g. from seed-to-seed runs of the good state
  repeats: 3
  max_repeats: 24
  confidence: 0.95       # diagnosis-level: P(wrong verified) <= 0.05 under A1-A3
```
