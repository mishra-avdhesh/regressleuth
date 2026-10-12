# Method

**Setting.** An incident has components `C` (model, preprocessing, config, data, environment, ...), a known-good version `g` and known-bad version `b` of each, and one fixed set of labeled cases with a metric. For `S ⊆ C`, the *hybrid* `x(S)` uses `b` for components in `S` and `g` otherwise. `F(S)` is true when `x(S)` crosses the declared regression threshold relative to `x(∅)`.

**Entry conditions.** `F(∅)` is false and `F(C)` is true, established by replaying both endpoints. Otherwise the result is `invalid_baseline` and nothing is attributed.

**Hypotheses.** A cause is a set `h` with `1 <= |h| <= max_cause_size` (default 2; 1 and 3 are opt-in). Under the model, `F(S)` holds exactly when `h ⊆ S` (a *monotone conjunction*). A cause is *minimal* if `F(h)` holds and every proper subset passes.

**Search.** Each replay with a definite outcome (pass or fail) removes every hypothesis that predicts the other outcome. The adaptive strategy replays the unseen mask whose predicted failures split the remaining hypotheses closest to evenly, which maximizes expected elimination under a uniform prior and unit cost. All other strategies share the same driver, cache, budget counter and elimination rule; they only differ in which mask they request. `ddmin` is Zeller and Hildebrandt's delta debugging over the changed components.

**Verification.** A unique remaining hypothesis is *minimality verified* once its own mask has failed and every non-empty proper subset has passed.

**Audit.** The monotone model is a modeling assumption, so after verification extra replays test it. The `full` audit (historical benchmark profile, at most `|C|` replays): removing a cause component from the all-bad state must pass, and adding any other bad component to the cause must still fail. The `extended` audit (new public default) also adds every pair of other components to the cause (must fail) and replays every single other component and every pair of them alone (must pass), which exposes latent failures that another change hides in the all-bad state. Any contradiction yields `assumption_violated` and the suspected cause is withheld. Without a complete audit the result is `inferred`, not `verified`. Audit replays are reported separately from the isolation budget. See [VERIFICATION.md](VERIFICATION.md).

**Noise.** With `repeats = r` and `max_repeats = R`, a hybrid is run `r` times and compared to the good baseline: with effect `d` (in the regression direction) and standard error `se` (unpooled), it is `fail` if `d - q·se ≥ τ`, `pass` if `d + q·se < τ`, otherwise `inconclusive` and more runs are added up to `R`. New incidents use the Student-t quantile at Welch's degrees of freedom; the archived benchmark used a normal quantile. The good baseline is run `r` times and not extended. Inconclusive replays prune nothing.

**Outcomes that are not evidence.** `incompatible` (hybrid cannot be built) and `error` (crash or timeout) never prune hypotheses and never count as a pass.

**Freeze.** The historical profile (normal interval, `full` audit, causes of at most two components) was frozen locally on 2026-10-08 with source hashes and a behavioral fingerprint of 1,872 replay sequences (`benchmarks/frozen/`). `python benchmarks/freeze_method.py verify` checks those replay traces. This was an internal freeze without an external timestamp; the safer public defaults are a subsequent change, not an untouched frozen method.

**What it does not claim.** Verification means "consistent with the replays performed under the stated model", not a causal proof: untested hybrids can still behave differently, causes larger than two components are not searched, and replays are assumed to depend only on the declared components. Larger-than-pairwise interactions surface as `assumption_violated`, not as a guess.
