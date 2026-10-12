# Addendum B, 2026-10-11 (IST), to the dependency-drift protocol

Written after the reports from the first candidate query were read, and **before any
candidate was replayed** (no resolution, installation or test run had happened).
`SELECTION_PROTOCOL.md` and addendum A are unchanged. These rules clarify cases that
the reports raised; they are applied to every candidate, including those already read.

**B1. Dates from linked runs.** A last passing or first failing CI run that the report
links counts as a stated date. Its run date (UTC) is used for `D_good` or `D_bad`.

**B2. Located tests.** A test counts as named when the report gives its node ID, its
class and function name, or a traceback line that falls inside exactly one test function
of the fixed commit. A parametrized test named without parameters means all of its
parameters.

**B3. Coupled causes.** Mixing versions can make a proper subset of a failing mask
uninstallable, for example when a newer dependency is needed before a newer library can
be installed at all. Such a mask is **coupled-minimal** if it fails, at least one proper
subset is incompatible, and no compatible proper subset fails. Ground truth lists strict
minimal failing sets (every proper subset compatible and passing) and coupled-minimal
sets separately. Both count as accepted causes, and an incident whose blamed distribution
appears in either is not disputed for that reason. Incidents with a coupled-minimal cause
form their own stratum. Regressleuth cannot `verify` such a cause (its proper subsets
cannot pass), so `inferred` is the best correct outcome there; a wrong `verified` still
counts as wrong.

**B4. Release-based reports.** When a report concerns a released version of the project
(for example a distribution packaging the release), the fixed commit is that release's
tag, and the requirement set is the one that release declares (runtime plus its declared
test extra, or `pytest` if it declares none).

**B5. Non-candidates.** A result that reports no test or CI failure, or attributes the
failure to nothing, is not a candidate. Such results are listed in `SEARCH_LOG.md`, not
the ledger.
