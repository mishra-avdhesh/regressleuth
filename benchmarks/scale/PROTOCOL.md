# Large-search-space study protocol

**Written and frozen before its run** (2026-10-11 IST). `FREEZE.json` hashes this file,
`scale.py` and `src/regressleuth`; `scale.py run` refuses to start if any changed and
refuses to overwrite results.

## Question

How do search, verification and audit behave as the number of changed components
approaches the engine's cap of 12 (search spaces of 256, 1,024 and 4,096 states)? What do
they cost in replays and in the engine's own time and memory? This study uses synthetic
oracle incidents, which satisfy the method's model by construction (except the
non-monotone control). It is evidence about scaling and cost, **not** about external
validity. External large-space evidence comes only from the dependency-drift suite.

## Design

- `k` in {8, 10, 12} changed components; deterministic replays (one run each).
- Scenarios, 100 incidents per (scenario, k), each defined by its seed:
  - `single`: one random cause component.
  - `pair`: a random pair that fails only together.
  - `masked_healing` (non-monotone control): cause `C` (one or two components), healer
    `h` and guard `g`. A mask fails iff `C` is bad and not (`h` bad and `g` good). The
    known-bad state fails.
- All six strategies; isolation budgets 8, 12, 16, 24, 32 and the full space `2^k`; random
  search uses seeds 0–4; `extended` audit; causes of at most two components (defaults).
- Correct means the diagnosis is one of the true minimal failing sets (computed
  exhaustively).

## Outcomes

Per (scenario, k, strategy, budget): wrong `verified` (first), correct `verified`,
`inferred`, `unresolved`, `assumption_violated`, mean isolation, audit and total replays,
and engine time and peak traced memory per investigation, excluding replay execution
(replays are instantaneous oracles).

Pre-registered checks:

1. **Feasibility at the cap.** At `k = 12`, every strategy's mean engine time per
   investigation is below 2 s, and its peak traced memory is below 256 MB.
2. **Safety at scale.** Wrong `verified` counts on `single` and `pair` are reported. On
   `masked_healing`, any wrong `verified` is reported as a failure of the `extended` audit
   at that size.
3. **Search efficiency.** Adaptive's and ddmin's isolation replays before a correct
   `verified` at the full budget are compared, per `k` and scenario, with an exact
   two-sided sign test over the paired incidents. The comparison is descriptive: these
   incidents satisfy the model that adaptive search was designed for.

Nothing is changed after the run; results are reported as found.
