# Release checklist (manual steps)

This checkout is prepared as `0.1.0a1`. No remote, tag, package upload, or Space
deployment has been made. The maintainer performs every account and publication step
below. Keep the version at `0.1.0a1` for the alpha; `0.1.0` requires a separate decision.

The historical pilot validates only single-component replay. The two separately sealed
dependency-drift studies (issue reports and lockfile-update pull requests) yielded zero
eligible incidents, so independent multi-component search and interaction evidence is
still missing. Do not use that study as a performance
or false-verification claim; review [the benchmark report](docs/BENCHMARKS.md#dependency-drift-study-zero-eligible-incidents)
before deciding on a stable release.

## 0. Local checks (all must pass)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[demo,dev,lockfiles]"
pytest --cov=regressleuth --cov-report=term-missing --cov-fail-under=90
ruff check . && ruff format --check . && mypy --strict
python benchmarks/freeze_method.py verify
python benchmarks/seal.py verify benchmarks/holdout --definitions-only
python benchmarks/seal.py verify benchmarks/higher_order --definitions-only
python benchmarks/historical/verify_snapshot.py
python benchmarks/snapshot.py verify benchmarks/drift
python benchmarks/snapshot.py verify benchmarks/lockdrift
python tools/check_lockfile_example.py             # real uv, pandas upgrade
python -m build && twine check dist/* && python tools/audit_package.py dist/*
python -m venv /tmp/rl-clean && /tmp/rl-clean/bin/pip install dist/*.whl
/tmp/rl-clean/bin/regressleuth --version && /tmp/rl-clean/bin/regressleuth demo
```

## 1. Before creating the repository

- Re-check the exact `regressleuth` name on PyPI and the intended GitHub/Hugging Face
  namespaces immediately before publication. Search results alone do not establish
  availability. If the PyPI name is unavailable, choose a new distribution name and
  update the package metadata, Space pin, and release instructions before uploading.
- Review `git ls-files` for private planning notes, prompt files, generated artifacts,
  credentials and machine-specific paths before creating a remote repository.
  `FINAL_PLAN.md` is a local planning note and is ignored by Git.
- Confirm the GitHub project URL in `[project.urls]` matches the public repository.
  Rebuild the distributions after changing metadata. Add an ORCID to `CITATION.cff`
  if you have one.
- The free static Space in `space_static/` can be hosted before PyPI publication; it
  contains precomputed reports and needs no server or API. Regenerate it after changing
  the demo code or package version with `python tools/build_static_space.py`.
- The optional live Gradio template in `space/` pins `regressleuth==0.1.0a1`; deploy
  it only after that version exists on PyPI and if its hosting cost is acceptable.

## 2. GitHub (not yet done)

```bash
git status --short                    # should be empty before pushing
git ls-files                          # review public paths again
git diff HEAD --check                 # review any later changes
# Create an empty public repository on GitHub, then:
git remote add origin https://github.com/mishra-avdhesh/regressleuth.git
git push -u origin main
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

## 4. PyPI alpha (`0.1.0a1`)

1. On PyPI, add a pending trusted publisher (same fields, environment `pypi`).
2. In the GitHub repository create an environment named `pypi` (Settings, Environments),
   with required reviewers if desired. Approve the deployment only after reviewing
   the build artifact and the TestPyPI rehearsal.
3. Confirm `pyproject.toml`, `src/regressleuth/__init__.py`, `CITATION.cff`, the Space
   pin, and the release notes all say `0.1.0a1`. When the package is published,
   replace the README's "once released" install note and date the `0.1.0a1`
   changelog entry in the release commit.
   Push that commit to `main` and confirm its CI checks. Then,
   when ready to publish, run `git tag v0.1.0a1 && git push origin v0.1.0a1` manually.
   **Pushing this tag triggers PyPI publication** through `release.yml`; pushing
   `main` alone does not. The workflow checks version equality, tests, lint, types,
   method freeze, seals, package contents, and then publishes via trusted publishing.
4. Confirm `pip install regressleuth==0.1.0a1` and `regressleuth demo` in a clean
   environment. Mark the GitHub Release as a pre-release and use the `0.1.0a1`
   changelog section as notes.

## 5. Hugging Face Space (free static route)

Create a public **Static** Space at
`https://huggingface.co/spaces/avdheshmishra/regressleuth` and copy the contents
of `space_static/` to its repository root. The URL without `/spaces/` is a model
repository and does not host this app. One command-line route is:

```bash
python -m pip install -U huggingface_hub
hf auth login
hf repo create avdheshmishra/regressleuth --repo-type space --space-sdk static
hf upload avdheshmishra/regressleuth space_static . --repo-type space
```

Check that both the pair example
and double-healer control load with `extended` and historical `full` audits, and that
the full reports open. The eight reports are snapshots made by the actual engine;
selection in the browser does not run a new investigation. This route needs no
package installation, API key, or paid compute. It can also be hosted on GitHub Pages.
Add the final Space URL to the GitHub README after deployment.

The live Gradio template remains in `space/` for local use or an account with paid
compute access. As of October 2026, Hugging Face requires a paid plan to create a
new Gradio or Docker Space, even on CPU Basic; [Static Spaces are free for everyone](https://huggingface.co/docs/hub/main/spaces-sdks-static).

## 6. Stable release (`0.1.0`, separate decision)

Do not infer stable-release readiness from a successful alpha upload. Review the
limitations in [the roadmap](docs/ROADMAP.md) and the dependency-drift negative
result first. If a stable release is justified, update versions in `pyproject.toml`,
`src/regressleuth/__init__.py`, `CITATION.cff`, the Gradio Space pin, the static
snapshots, and `CHANGELOG.md`;
rerun section 0; commit. Then the manually pushed `v0.1.0` tag follows the same
PyPI workflow. PyPI does not permit replacing an uploaded version.
