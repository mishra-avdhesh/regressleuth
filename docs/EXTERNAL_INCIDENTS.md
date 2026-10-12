# Submit a reproducible external incident

Regressleuth still lacks an independently curated, real incident with several changed
components. The existing historical pilot contains only single-component changes; the
separate dependency-drift study had no eligible incidents. A public issue with a working
good/bad replay is more useful than another constructed example.

## What to send

Open the [external incident issue template](../.github/ISSUE_TEMPLATE/external_incident.yml)
with these materials, or link to a public repository that holds them:

1. The original issue, outage report, or failing pull request, dated before this submission,
   and the independent fix or maintainer analysis if one exists.
2. Exact good and bad component manifests: model artifact digest, preprocessing commit,
   configuration revision, package lock, and data snapshot ID where applicable. List every
   changed component and keep unchanged dependencies pinned.
3. One fixed evaluation set with stable case IDs, labels kept outside swappable artifacts,
   metric code, direction, threshold, and a command that runs **both** endpoint states.
4. The observed good and bad outputs, their logs, runtime, machine requirements, and an
   explanation of which hybrids are feasible. Include the original failure signature so
   a new replay is not mistaken for the reported incident.
5. Artifact access and license terms. Use public or shareable test data; never post secrets,
   private customer records, credentials, or proprietary weights in the issue.

An incident with one changed component can still test the replay workflow. Evidence for
search or pair interactions needs two or more independently versioned changes and
replayable hybrid states. A case whose good state fails or bad state passes remains useful
as a **disputed** candidate; it is not counted as a successful diagnosis.

## How it is evaluated

The submitter can run `regressleuth validate incident.yaml` and `regressleuth inspect
incident.yaml` without performing a diagnosis. Maintainers first reproduce the fixed test
and record candidate and exclusion decisions. If a future external study is approved, it
gets a new dated protocol and ledger **before** strategies are run. Ground truth is based
on the original issue/fix and, where feasible, exhaustive hybrid replay. The suite is
sealed before a one-time, equal-observation comparison of all strategies. Existing sealed
studies and their reported numbers are never changed to fit a new case.

Independent curation matters: a contributor who did not design the search should check
at least a subset of eligible cases and disputed outcomes. Until that happens, the project
will continue to label external search and interaction performance as unestablished.
