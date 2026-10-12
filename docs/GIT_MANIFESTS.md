# Compare versioned artifact manifests in Git

`manifest-diff` reads a JSON component map from two commits in a local Git repository.
It pins each ref to a commit ID, compares component values, and runs no model replay.
The repository and working tree are not changed.
Objects missing from a partial clone are not fetched; fetch them separately before
running the comparison.

Store the same relative file path in both commits, for example `deploy/artifacts.json`:

```json
{
  "model": "sha256:good-model-digest",
  "preprocessing": "preprocessing-commit-id",
  "threshold_config": "config-v4"
}
```

Use stable artifact IDs, image digests, or commits as values. The manifest is an ordinary
Git file, so keep credentials out of it. Values may be any finite JSON value, but a flat
map of strings is easiest to replay. Component names must match Incident Specification 1.0.

```bash
regressleuth manifest-diff . GOOD_COMMIT BAD_COMMIT deploy/artifacts.json
regressleuth manifest-diff . GOOD_COMMIT BAD_COMMIT deploy/artifacts.json \
  --include-values --output local-diff.json
```

The default JSON output lists changed, added, and removed component names; unchanged
components are counted. It also records both commit IDs and SHA-256 hashes of the exact
manifest bytes. It does not include version values or the local repository path.
`--include-values` adds `good` and `bad` maps for local incident preparation. Common
credential keys and secret-looking values are redacted. Review the local output before
sharing it; arbitrary secrets cannot be detected reliably.

To investigate, copy the `good` and `bad` values into an incident file, then configure
an adapter that can actually load each selected version and each relevant hybrid. The
command does not create a runnable incident, prove that artifacts are available, or
validate hybrid replay. Added and removed keys need an explicit replayable representation
on both sides: Incident Specification 1.0 requires the same component keys in `good`
and `bad`. The diagnosis engine supports at most 12 changed components.

The manifest path must be a relative POSIX path and exist as a blob at both commits.
The input limit is 1 MiB per manifest. The command exits 0 for a valid comparison,
including one with no changed values, and 3 for invalid input. These exit codes describe
the comparison only; they are not diagnosis statuses.
