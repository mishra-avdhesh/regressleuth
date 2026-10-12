# Release checklist (manual steps)

Nothing in this repository has been published. A local `main` commit for `0.1.0a1` is
prepared, with no remote or tag. Version stays `0.1.0a1` until the maintainer approves
`0.1.0`. Remote and publication steps below are for the maintainer to perform.

The historical pilot validates only single-component replay. The separately sealed
dependency-drift study yielded zero eligible incidents, so independent multi-component
search and interaction evidence is still missing. Do not use that study as a performance
or false-verification claim; review [the benchmark report](docs/BENCHMARKS.md#dependency-drift-study-zero-eligible-incidents)
before deciding on a stable release.

## 0. Local checks (all must pass)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[demo,dev]"
pytest --cov=regressleuth --cov-report=term-missing --cov-fail-under=90
ruff check . && ruff format --check . && mypy --strict
python benchmarks/freeze_method.py verify
python benchmarks/seal.py verify benchmarks/holdout --definitions-only
python benchmarks/seal.py verify benchmarks/higher_order --definitions-only
rm -rf dist && python -m build && twine check dist/* && python tools/audit_package.py dist/*
python -m venv /tmp/rl-clean && /tmp/rl-clean/bin/pip install dist/*.whl
/tmp/rl-clean/bin/regressleuth --version && /tmp/rl-clean/bin/regressleuth demo
```

## 1. Before creating the repository

- Re-check the name: `https://pypi.org/project/regressleuth/` should return 404, and
  `https://github.com/<you>/regressleuth` should not exist.
- Review the staged Git index for private planning notes, prompt files, generated artifacts,
  credentials and machine-specific paths before committing or creating a remote repository.
  `FINAL_PLAN.md` is a local planning note and is ignored by Git.
- Confirm the author in `CITATION.cff` and configure the intended Git commit name and email.
  Add an ORCID if you have one.
- The Space template pins `regressleuth==0.1.0a1`; deploy it only after that exact version
  exists on PyPI, and update the pin for later releases.

## 2. GitHub (not yet done)

```bash
git status --short                  # should be empty before creating a remote
git ls-files                        # review public paths again
git diff HEAD --check               # review any later changes
gh repo create <you>/regressleuth --public --source . --push      # or create it on github.com
```

Then on GitHub: add a description and topics (machine-learning, debugging, mlops,
root-cause-analysis); enable private vulnerability reporting (Settings, Security); check that
the CI workflow passes on all three Python versions.

## 3. TestPyPI rehearsal

1. Create accounts on https://test.pypi.org and https://pypi.org; enable 2FA.
2. In the GitHub repository, create an environment named `testpypi` (Settings, Environments).
   On TestPyPI, add a *pending trusted publisher*: project `regressleuth`, owner `<you>`,
   repository `regressleuth`, workflow `release.yml`, environment `testpypi`.
3. From the `main` branch, manually run the **Release** workflow in GitHub Actions with
   `publish_testpypi` selected. Its default is off, so an ordinary manual run only checks
   and builds. Selecting it runs tests, lint, type, freeze and seal checks, audits the
   package, then publishes to TestPyPI.
   Run it once per package version; TestPyPI does not allow uploading the same version twice.
4. Install from TestPyPI in a clean environment:
   `pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ regressleuth==0.1.0a1`
   and run `regressleuth demo`.

## 4. PyPI

1. On PyPI, add a pending trusted publisher (same fields, environment `pypi`).
2. In the GitHub repository create an environment named `pypi` (Settings, Environments),
   optionally with required reviewers.
3. When approved for release, change the version to `0.1.0` in `pyproject.toml` and
   `src/regressleuth/__init__.py`, update `CITATION.cff` and `CHANGELOG.md`, commit, then
   `git tag v0.1.0 && git push origin v0.1.0`. The `release.yml` workflow reruns tests,
   lint, type, freeze and seal checks, verifies that the tag matches the package version,
   then builds and publishes to PyPI. Check that the workflow passes before announcing the release.
4. Create the GitHub Release from the tag with the CHANGELOG section as notes.

## 5. Hugging Face Space (optional)

Create a Gradio Space, copy `space/app.py`, `space/requirements.txt` (pointing at the released
package or the GitHub repository) and `space/README.md`. The Space runs only the built-in oracle
incidents and executes no user code.
