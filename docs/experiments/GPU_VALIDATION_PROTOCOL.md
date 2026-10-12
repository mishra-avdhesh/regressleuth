# Exploratory GPU validation protocol

**Status (2026-10-09): planned, not run.** This is an exploratory stress test, separate from the
frozen development and sealed holdout suites. It cannot establish research novelty or an
independent production validation by itself.

## Why it is pending

`nvidia-smi` reports two idle NVIDIA RTX 6000 Ada GPUs with 49,140 MiB each and about
48,500 MiB (47.4 GiB) free per GPU. The only local Python on `PATH` is `/usr/bin/python3`; its installed
`torch 2.14.1+cpu` and `torchvision 0.29.1+cpu` report
`torch.backends.cuda.is_built() == False` and `torch.cuda.is_available() == False`.
No local `libtorch_cuda.so` was found. Running a GPU trial therefore requires installing a
CUDA-enabled build in an isolated environment. No GPU result is claimed here.

## Question

Does the existing, frozen unit-cost adaptive search correctly diagnose real neural-network
regressions with 8–10 independently versioned components, and how do its **total replays and
measured end-to-end replay time** compare with `ddmin` under the same evidence and audit rules?
This is a scalability and deployment-cost question. The current selector optimizes the expected
number of masks, not wall time; a wall-time advantage is a measurement to test, not a property
to assume.

## Design, to lock before running any strategy

1. Use a fresh isolated Python environment with a CUDA-enabled PyTorch and record exact Python,
   CUDA, driver, GPU, PyTorch and torchvision versions. Use one GPU for the primary experiment;
   keep the second unused, so concurrent execution does not confound timings. Do not change the
   frozen search code or the sealed holdout.
2. Use the public MNIST train/test data already cached locally from `ylecun/mnist`. Record its
   repository revision and SHA-256 hashes of the source files. Train two small CNN checkpoints
   with a fixed architecture, split, seed, optimizer and epoch count. Keep the same fixed labeled
   evaluation cases for **every** hybrid replay. Record source and checkpoint hashes. The model
   is trained once per version, never within a replay.
3. Construct 8–10 independently selectable, plausible release components, for example model
   checkpoint, orientation transform, resize mode, quantization, normalization, crop/pad rule,
   input precision, confidence policy and batch configuration. Give each a concrete old/new
   artifact or value. Do not count duplicate aliases or inert flags as separate changes. A
   proposed interaction such as checkpoint × orientation may be included, but **retain all
   constructed incidents**, including ones with no qualifying regression, multiple causes or
   incompatible hybrids. Record construction rules and the metric threshold before inspecting
   strategy outcomes.
4. Use inference only, fixed cases, deterministic transforms, `model.eval()`, fixed seeds and
   `torch.use_deterministic_algorithms(True)` where supported. Run the same metric table for all
   strategies. For each mask, record accuracy, status, elapsed replay seconds and GPU peak memory;
   give endpoints and audits the same treatment. Run all `2^k` masks to establish the complete
   truth table and check whether the single monotone cause assumption actually holds. This
   exhaustive construction cost is reported separately from diagnosis cost.
5. Replay the stored table with the frozen `adaptive`, `ddmin`, `greedy`, `random`, one-factor and
   exhaustive strategies. Use the identical metric observations, seed, isolation budget and
   **audit mode** for each. Report budgets of 8, 12, 20 and 32 masks plus full enumeration.
   Run random search with at least 10 fixed seeds. Report verified-and-correct, false verified,
   `inferred`, `unresolved`, `assumption_violated`, isolation masks, total masks **including
   endpoints and audit**, and measured total replay seconds. The existing isolation budget
   excludes audit, so give both budgeted isolation and actual total cost. Do not equate a count
   of masks with a wall-time budget when masks have different costs.
6. For timed trials, measure two operational modes separately: a fresh subprocess for each mask
   (the command-adapter deployment) and a persistent loaded model worker (the Python-adapter
   deployment). Apply the same mode to every strategy, warm up the GPU identically, synchronize
   CUDA around each timed replay, and record cold-start overhead. With a stored table, sum each
   strategy's observed per-mask times; optionally rerun strategies end to end as a cross-check.

## Reporting rule

Publish each incident's full truth-table status and per-strategy results, including failures and
invalid baselines. Show confidence intervals across **incidents**, not over masks from one
incident. If there are fewer than roughly ten independently constructed incidents, show counts
and individual cases without a broad superiority claim. Any adjustment to method, threshold,
components or checkpoint after viewing outcomes starts a new development experiment and must be
logged. A designed MNIST suite can support a speed or scale claim in that setting; it cannot
close the remaining novelty gap with CULPA or substitute for independently sourced incidents.

## Stop conditions

- CUDA PyTorch is unavailable or dependencies require a substantial download during this run.
- The hardware does not support deterministic execution needed for the chosen model, unless the
  remaining variation is measured and reported as noise.
- Exhaustive truth-table construction exceeds the agreed compute window; reduce the component
  count **before** evaluating any search strategy and record that change.
