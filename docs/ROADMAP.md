# Research and product roadmap

This roadmap starts from the unreleased `0.1.0a1` alpha. Normal incidents use the
`extended` audit and Student-t intervals; the historical `full`/normal benchmark profile
and its results remain frozen. None of the milestones below changes those stored results.

## Release gates, in order

| Gate | Work | Evidence needed before claiming success |
|---|---|---|
| 1. Independent evidence | Write an incident selection and exclusion protocol before collecting cases. Pilot 10–15 externally sourced, reproducible regressions; expand toward 30–50 only if enough cases meet the criteria. | Public source issue/PR; immutable good/bad component IDs and hashes; fixed cases and metric; feasible hybrids; independently established culprit or an explicit set of valid causes. Record exclusions and have someone who did not design the search curate a subset. Seal the evaluation set before running methods. |
| 2. Noisy verification | Replace per-look, per-mask Student-t decisions with a prespecified error-control procedure, or keep noisy findings below `verified` until validated. Candidate approaches are fixed repeats with a familywise correction or time-uniform confidence sequences with a declared bound on the number of masks. | Simulation under stated noise assumptions and untouched noisy controls; measured false-verification rate with uncertainty; tests for optional stopping, shared baseline, multiple masks, and non-Gaussian noise. A nominal 95% replay interval is not a 95% diagnosis guarantee. |
| 3. Audit and scale | Keep `extended` as the user default. Reuse observed masks (already implemented) and stop the audit when a definite contradiction is found. Measure search and audit separately at 8, 10, and 12 changed components. Raise the current 12-component cap only after profiling and making mask generation/scoring scale. | Time, memory, runner runs, audit masks, correct verification, and incorrect verification at each size. With a two-component candidate, `extended` can plan 44/74/112 masks at 8/10/12 components before reuse; a 15-component run can plan 184. A partial risk-based audit must report `inferred` unless its narrower assumptions and error bound are established. |
| 4. Cost-aware evaluation | Record predicted and actual replay cost, wall time, GPU seconds, setup time, and cache hits. Select experiments by an explicit gain-per-cost rule and account for audit cost. | Compare with exhaustive, random, one-factor, and cost-aware delta debugging at equal total cost and equal verification requirements. Report time to a correct verified diagnosis and unresolved/error rates, not only replay counts. |
| 5. Non-monotone model | Define a limited hypothesis class for sparse main effects, pair interactions, cancellation/healing, and selected three-way effects. Specify which masks can distinguish competing explanations. | Hidden interaction controls and external incidents; calibration or abstention when several models fit. For an arbitrary Boolean failure function, untested masks can conceal a contradiction, so a universal false-verification guarantee needs exhaustive checking or explicit structural assumptions. |
| 6. Real replay | Reproduce one versioned vision or text incident on fixed cases using the available GPUs; preserve artifact digests, seeds, environment, and timing. Validate the Docker adapter on a host with a working daemon. | End-to-end wall time and GPU seconds per replay; timeout, failure, cleanup, path/volume, environment, isolation, and resource-limit tests for containers. Keep the adapter experimental until those checks pass. |
| 7. Product workflow | Start with read-only extraction of changed artifacts from Git and one experiment tracker. Add further trackers and artifact stores after a common versioned manifest format is stable. Start multi-metric incidents with one target regression and explicit guardrails for latency, memory, or accuracy. | Deterministic artifact mapping, no secrets in reports, integration tests using pinned fixtures, and clear behavior when objectives conflict or an artifact cannot be replayed. |

Gate 1 status (2026-10-13): still not met. Two further pre-registered studies (dependency drift v1 and lockfile updates v2, 80 public candidates) found no eligible multi-component incident; see BENCHMARKS.md. Earlier status (2026-10-10): the selection protocol and a first pilot exist. 30 public
reports were screened; 9 single-component regressions reproduced in matched environments,
were sealed, and produced no wrong `verified` diagnosis
([details](BENCHMARKS.md#external-historical-pilot-9-public-regressions-sealed-evaluated-once)).
A second pre-registered dependency-drift search (2026-10-11) logged 40 reports: 33 were
excluded and all 7 controlled replays were disputed, leaving zero eligible incidents
([details](BENCHMARKS.md#dependency-drift-study-zero-eligible-incidents)). The gate is not
met: no externally sourced incident with two or more changed components was verified,
and no one independent of the search design has curated a subset. Next sources to try
are reproducible bug collections and post-mortems that ship pinned artifacts, not issue
trackers. A new study needs its own protocol and sealed evaluation set; the two completed
studies remain unchanged.

Gate 2 status (2026-10-11): `interval: anytime` implements a diagnosis-level bound (proof in
VERIFICATION.md). Two pre-registered simulations covered optional stopping, a shared baseline,
many masks, non-monotone truth, misdeclared noise and heavy tails; they found no wrong
`verified` with it, while per-comparison intervals did produce wrong ones near the threshold.
Open items: untouched *real* noisy controls, and power (it abstains near the threshold and
costs about 40% more runs).

Gate 3 status (2026-10-11): measured at 8, 10 and 12 components (time, memory, isolation and
audit replays, correct and wrong `verified`). The engine is cheap (0.37 s, under 3 MB per
investigation at 12); the `extended` audit is not (about 131 replays for a single cause at
12). The cap stays at 12 until the audit becomes incremental or risk-based with its own
error analysis.

Gate 7 status (2026-10-11): a read-only Git manifest comparison is available. It pins
commit IDs and hides values by default. Experiment tracker integration, multi-metric
guardrails, and proof that extracted artifacts can be replayed remain open.

## Benchmark protocol

Historical bugs count only when the good state, bad state, fixed evaluation data, metric,
changed component boundaries, and relevant hybrid combinations can be reconstructed.
Record cases rejected because they cannot meet those requirements. Keep development,
independent validation, and final holdout sources separate. Do not tune search or audit on
the final holdout. Compare each method under the same observations, isolation budget,
audit policy, and measured cost. Report paired per-incident outcomes and uncertainty;
do not infer general superiority from a small author-built suite.

The existing 0/60 false-verification result on two known non-monotone controls is a useful
regression test. Those configurations share the same two incidents, and the `extended`
audit was designed after the controls were seen; they are not 60 independent safety trials.

## Claims and prior work

The contribution must be stated against delta debugging, ML pipeline debugging, and
counterfactual hybrid-replay attribution. A prospective research claim is budgeted
diagnosis with explicit abstention under declared interaction, noise, and replay-cost
assumptions. Algorithmic novelty and a probability bound on incorrect verification require
new analysis and independent evidence; they are not properties of the current alpha.

Do not promote `0.1.0a1` to a stable `0.1.0` on the strength of the existing controls alone.
The minimum stable-release decision should include the noisy-verification gate, the
independent safety evaluation, and accurate user-facing scope for `verified`.

Primary work to compare directly: [delta debugging](https://www.st.cs.uni-saarland.de/papers/tse2002/),
[Maro's ML pipeline debugging](https://arxiv.org/abs/2205.01311), and
[CULPA's hybrid-replay pipeline attribution](https://github.com/laiba-mazhar/culpa-pipeline-attribution/blob/main/PAPER.md).
[Time-uniform confidence sequences](https://arxiv.org/abs/1810.08240) are one candidate
tool for sequential metric decisions. A historical bug collection such as
[defect4ML](https://arxiv.org/abs/2206.12311) can supply leads, but its bugs still need
screening for versioned component swaps and valid hybrid replays.
