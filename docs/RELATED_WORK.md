# Related work: what exists, and what Regressleuth might add

Written 2026-10-13 as a gate before further method work. The claim under scrutiny is
budgeted counterfactual search over versioned pipeline components, including interaction
failures, with explicit verification and assumption-violation handling. **Most of its
ingredients exist.** What may be new is narrow and mostly engineering and evaluation
practice, not a new algorithm.

This is a targeted comparison, not a systematic novelty review. The cited papers and
project pages are linked below so the overlap can be checked directly.

## 1. Isolating failure-inducing changes (delta debugging)

- **[Zeller (ESEC/FSE 1999), "Yesterday, my program worked. Today, it does not. Why?"](https://www.st.cs.uni-saarland.de/publications/details/zeller-esec-1999/)**
  This applies delta debugging to the set of changes between a working and a failing
  version, and isolates the failure-inducing subset by testing partial change sets. That
  is Regressleuth's problem statement, with source changes instead of artifact versions.
  Hybrid states that cannot be built ("unresolved" tests) were already part of that
  setting.
- **[Zeller and Hildebrandt (TSE 2002), "Simplifying and isolating failure-inducing input."](https://www.st.cs.uni-saarland.de/papers/tse2002/)**
  The `ddmin` algorithm. It is Regressleuth's main baseline.
- **Probabilistic Delta Debugging (ProbDD)**, Wang, Shen, Chen, Xiong and Zhang, ESEC/FSE
  2021. It keeps a probability model over which elements matter and picks the most
  informative next test, instead of ddmin's fixed schedule. Its worst-case test count is
  O(n), against ddmin's O(n²).
  [paper page](https://2021.esec-fse.org/details/fse-2021-papers/94/Probabilistic-Delta-Debugging)
- **"Toward a Better Understanding of Probabilistic Delta Debugging"** (ICSE 2025) analyzes
  ProbDD and proposes a simpler variant, CDD, with the same performance. It also notes that
  ProbDD trades away 1-minimality guarantees. [arXiv 2408.04735](https://arxiv.org/abs/2408.04735)
- **"Accelerating Delta Debugging through Probabilistic Monotonicity Assessment"** (2025
  preprint) assesses monotonicity probabilistically during reduction.
  [arXiv 2506.11614](https://arxiv.org/abs/2506.11614)

**Overlap.** Adaptive next-test selection and reasoning about monotonicity both exist in the
delta-debugging literature. Regressleuth's adaptive strategy is not new in kind, and its
audit is related to monotonicity assessment. ProbDD, CDD and the monotonicity-assessment
approach are missing baselines.

## 2. Group testing, including complexes and inhibitors

- [Dorfman (1943)](https://doi.org/10.1214/aoms/1177731363) introduced pooled tests for
  finding rare positive items.
- **Complexes.** A positive is a *set* of items that must all be present, as in our pair
  and triple causes. [Torney's sets-pooling model (1999)](https://doi.org/10.1007/BF01609879)
  and [group testing for complexes](https://doi.org/10.1016/S0166-218X(03)00191-4)
  already study this type of pooled outcome.
- **Inhibitors.** A test can become negative when an inhibitor is present alongside a
  positive. [De Bonis (2008)](https://doi.org/10.1007/s10878-007-9085-1) studies this
  setting and cites the earlier model of Farach and colleagues.

**Overlap.** Finding a minimal failing set of at most two changed components is adaptive
group testing for one positive complex. A "healing" change that hides a failure behaves like
an inhibitor. Query-count bounds for these settings exist and should be cited instead of
re-derived. The `assumption_violated` status is our response to the inhibitor-like case: we
abstain instead of identifying the inhibitor.

## 3. Learning with queries and generalized binary search

- **Angluin, "Queries and concept learning"** (Machine Learning 2, 1988) introduced the
  membership-query model. Identifying an unknown monotone conjunction of at most d of k
  variables with membership queries is a standard exact-learning problem, and our search
  is that problem with d = 2. [PDF](https://homepages.math.uic.edu/~lreyzin/papers/angluin88.pdf)
- **Nowak, "The geometry of generalized binary search"** (arXiv 0910.4397, 2009–2013) gives
  conditions under which greedily splitting the hypothesis set needs about log N queries
  for N hypotheses, and a noise-tolerant variant. Regressleuth's adaptive strategy, which
  picks the replay that best splits the remaining causes, is an instance of generalized
  binary search. [arXiv](https://arxiv.org/abs/0910.4397)
- [Dasgupta (NeurIPS 2004)](https://papers.nips.cc/paper_files/paper/2004/hash/c61fbef63df5ff317aecdc3670094472-Abstract.html)
  analyzed a greedy active-learning strategy in a related query setting.

**Overlap.** The search principle and its approximate-optimality theory exist. A new claim
would need a new setting or bound, for example one with audit cost and incompatible
hybrids counted.

## 4. Debugging computational and ML pipelines

- **BugDoc** (Lourenço, Freire, Shasha; SIGMOD 2020) finds minimal *definitive* root causes
  of pipeline failures by running new pipeline instances. Causes are parameter-value
  conjunctions and include software versions. Its Shortcut algorithm finds single
  conjunctions in a number of runs often linear in the number of parameters, and it is
  compared with Data X-Ray, Explanation Tables and SMAC.
  [arXiv 2004.06530](https://arxiv.org/abs/2004.06530)
- **"Debugging Machine Learning Pipelines"** (same authors, DEEM 2019 workshop) presents
  MLDebugger for ML pipelines. [arXiv 2002.04640](https://arxiv.org/abs/2002.04640)
- **[CULPA](https://github.com/laiba-mazhar/culpa-pipeline-attribution/blob/main/PAPER.md)**
  (a 2026 draft on hybrid replay for ETL fault attribution) and
  **[Maro](https://arxiv.org/abs/2205.01311)** (debugging AutoML pipelines) are related
  pipeline tools with different objectives and evidence.

**Overlap: this is the closest prior work.** Iteratively executing pipeline configurations to
find a minimal conjunctive root cause is BugDoc's problem. Regressleuth differs in setting
(each component has exactly a good and a bad version, versus parameter domains) and in
reporting (explicit `verified`, `inferred`, `assumption_violated`, an audit of the cause
model, a diagnosis-level noise bound). A direct comparison with BugDoc's Shortcut is the
most important missing baseline.

## 5. Anytime-valid inference (confidence sequences)

- **Howard, Ramdas, McAuliffe and Sekhon**, "Time-uniform, nonparametric, nonasymptotic
  confidence sequences", Annals of Statistics 49(2):1055–1080, 2021.
  [Project Euclid](https://projecteuclid.org/journals/annals-of-statistics/volume-49/issue-2/Time-uniform-nonparametric-nonasymptotic-confidence-sequences/10.1214/20-AOS1991.full)
- **Waudby-Smith and Ramdas**, "Estimating means of bounded random variables by betting",
  JRSS-B 2024 gives empirical-Bernstein and betting confidence sequences that adapt to
  variance. [arXiv 2010.09686](https://arxiv.org/abs/2010.09686)

**Overlap.** Our noise guarantee is a direct application: a normal mixture, a union bound
over masks, and a correctness argument for minimal failing sets. The proof is short
because the tools are mature. The power improvement planned for later (variance-adaptive
or betting sequences, budget only over planned masks) applies these papers; it does not
extend them.

## 6. Breaking dependency updates: benchmarks and tools

- **BUMP** (SANER 2024) has 571 reproducible breaking dependency updates from 153 Java/Maven
  projects. Each is a commit pair whose breaking commit changes one dependency version, with
  the tests passing before and failing after. [arXiv 2401.09906](https://arxiv.org/abs/2401.09906)
- **Breaking-Good** (2024) explains breaking updates from build logs.
  [arXiv 2407.03880](https://arxiv.org/abs/2407.03880)
- **where-broke** (npm) bisects *one* library's version history to find the version that
  broke the tests. **pyupcheck** (PyPI) predicts upgrade breakage statically from
  changelogs. A community thread proposes "time-machine" pip tools to find the last passing
  state. [where-broke](https://github.com/smeijer/where-broke),
  [pyupcheck](https://pypi.org/project/pyupcheck/),
  [thread](https://discuss.scientific-python.org/t/pinning-test-dependencies-with-regular-updates/711)
- [`git bisect`](https://git-scm.com/docs/git-bisect) handles ordered commits, not sets of
  simultaneous changes.

**Overlap and gap.** Breaking-update benchmarks exist for Java and focus on single-dependency
updates. A short search (2026-10-13, not systematic) found no tool that diagnoses *which of
several simultaneously changed Python distributions* broke the tests, by replaying
lockfile hybrids, with verification and abstention. It also found no Python benchmark of
multi-package lockfile regressions. Both are only "not found", not "do not exist".

## What may be new

1. **A practical, verified tool for multi-package dependency upgrades.**
   `regressleuth init --from-lockfiles` reads lockfiles for the target Python and platform,
   replays mixes of old and new versions, reports uninstallable ones as incompatible,
   checks installed files against their wheels' hashes, and verifies or abstains.
   (Engineering contribution.)
2. **Explicit verification semantics with an audited cause model**, plus a diagnosis-level
   error bound for noisy metrics, packaged for practitioners. (The parts are known; the
   combination and its tested failure modes are the contribution.)
3. **Pre-registered negative results on finding such incidents in public data.** Two
   protocols screened 80 public candidates and found no eligible multi-component incident.
   The funnels show why: late reports, CI layout and services, Python versions, git and
   custom-index sources, and update groups above the cap. Useful to anyone building a
   Python counterpart to BUMP.

## What is not new

Delta debugging over changes; adaptive or probabilistic next-test selection; group
testing for complexes and inhibitors; learning conjunctions with membership queries;
generalized binary search; iterative root-cause search over pipeline configurations
(BugDoc); confidence sequences.

## Gate decision for the planned phases

- **Phase 2 (cheaper audit)** overlaps with probabilistic monotonicity assessment (2025). Treat
  it as an engineering improvement with an explicit error statement, compared with that
  approach, not as a new method.
- **Phase 3 (singles first, then pairs)** is standard group-testing practice for complexes,
  and ProbDD/CDD are its natural comparators. Present it as a tuned strategy with
  baselines, not as a novel algorithm.
- **Phase 1 (a Python multi-package dataset)** is where something new is most likely. The
  two negative studies show it needs a different source (current CI logs and named failing
  tests) and wider support (Python versions, custom indexes, path dependencies).
