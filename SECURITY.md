# Security

Regressleuth executes a replay command you provide, as a local subprocess without a shell and with a timeout. **It is not a sandbox.** Run it only on code and artifacts you trust, and never point it at incident files from untrusted sources.

- Replay commands run with your user's permissions and environment.
- Lockfile incidents (`init --from-lockfiles`) install every pinned distribution from PyPI, or from the indexes the lockfile names, with uv, and then run your project's tests. Installing a package can run its build code (source distributions) and its import code, so only diagnose lockfiles whose packages and indexes you trust. `--wheels-only` avoids source builds. Installed files are checked against their wheels' RECORD hashes, which detects local tampering but not a malicious package.
- Model artifacts in the demos are trusted local pickles created by their `prepare.py` scripts; do not load pickles from untrusted places.
- New specification 1.0 reports omit component values by default. If you select `report.values: redacted`, short values that do not match known secret patterns appear in the report; pattern matching cannot guarantee confidentiality. Use `omit` for sensitive incidents. `hashed` exposes stable equality fingerprints.
- Replay stdout and stderr are not included in the report. The optional diagnostics directory stores local output tails and may contain sensitive data; control access to it and delete it when no longer needed.

To report a vulnerability, open a private security advisory on the GitHub repository rather than a public issue.
