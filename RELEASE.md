# Release checklist (manual steps)

This checkout is prepared as `0.1.0a1`. No remote, tag, package upload, or Space
deployment has been made. The maintainer performs every account and publication step
below. Keep the version at `0.1.0a1` for the alpha; `0.1.0` requires a separate decision.

The historical pilot validates only single-component replay. The separately sealed
dependency-drift study yielded zero eligible incidents, so independent multi-component
search and interaction evidence is still missing. Do not use that study as a performance
or false-verification claim; review [the benchmark report](docs/BENCHMARKS.md#dependency-drift-study-zero-eligible-incidents)
before deciding on a stable release.

## 0. Local checks (all must pass)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[demo,dev]"
pytest --cov=regressleuth --cov-report=term-missing --cov-fail-under=90
ruff check . && ruff format --check . && mypy --strict
python benchmarks/freeze_method.py verify
python benchmarks/seal.py verify benchmarks/holdout --definitions-only
python benchmarks/seal.py verify benchmarks/higher_order --definitions-only
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
- Add the final GitHub project URL to `[project.urls]` in `pyproject.toml` and the
  README when the owner and repository name are known. Rebuild the distributions
  after changing metadata. Add an ORCID to `CITATION.cff` if you have one.
- The Space template pins `regressleuth==0.1.0a1`; deploy it only after that exact version
  exists on PyPI, and update the pin for later releases.

## 2. GitHub (not yet done)

```bash
git status --short                    # should be empty before pushing
git ls-files                          # review public paths again
git diff HEAD --check                 # review any later changes
# Create an empty public repository on GitHub, then:
git remote add origin https://github.com/<owner>/regressleuth.git
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
   pin, and the release notes all say `0.1.0a1`. Replace the README's "not yet
   published" status and date the `0.1.0a1` changelog entry in the release commit.
   Push that commit to `main` and confirm its CI checks. Then,
   when ready to publish, run `git tag v0.1.0a1 && git push origin v0.1.0a1` manually.
   **Pushing this tag triggers PyPI publication** through `release.yml`; pushing
   `main` alone does not. The workflow checks version equality, tests, lint, types,
   method freeze, seals, package contents, and then publishes via trusted publishing.
4. Confirm `pip install regressleuth==0.1.0a1` and `regressleuth demo` in a clean
   environment. Mark the GitHub Release as a pre-release and use the `0.1.0a1`
   changelog section as notes.

## 5. Hugging Face Space (optional, after PyPI alpha)

Create a public Gradio Space in the chosen Hugging Face namespace. Copy the contents
of `space/` to the Space repository root: its `README.md` sets Python 3.12 and
Gradio 6.30.0, `requirements.txt` pins the PyPI alpha, and `app.py` runs the demo.
Check the Space build log and try the built-in pair example and double-healer
control. The Space executes no submitted user code. Add the final Space URL to
the GitHub README after deployment.

## 6. Stable release (`0.1.0`, separate decision)

Do not infer stable-release readiness from a successful alpha upload. Review the
limitations in [the roadmap](docs/ROADMAP.md) and the dependency-drift negative
result first. If a stable release is justified, update versions in `pyproject.toml`,
`src/regressleuth/__init__.py`, `CITATION.cff`, the Space pin, and `CHANGELOG.md`;
rerun section 0; commit. Then the manually pushed `v0.1.0` tag follows the same
PyPI workflow. PyPI does not permit replacing an uploaded version.
