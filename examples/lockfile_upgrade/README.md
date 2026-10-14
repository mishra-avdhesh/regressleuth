# A dependency upgrade, diagnosed from two lockfiles

`project/` is a tiny feature package with one test. `good.txt` and `bad.txt` are its
dependencies resolved as of 2026-01-15 and 2026-02-10 (`uv pip compile --exclude-newer`).
Between those dates five distributions changed:

| distribution | good | bad |
|---|---|---|
| numpy | 2.4.1 | 2.4.2 |
| packaging | 25.0 | 26.0 |
| pandas | 2.3.3 | 3.0.0 |
| pytz | 2025.2 | absent |
| tzdata | 2025.3 | absent |

The test passes with the good set and fails with the bad one, because pandas 3 removed
`DataFrame.applymap`. Which change broke it?

```bash
pip install -e ".[lockfiles]"          # Regressleuth plus uv
cd examples/lockfile_upgrade
regressleuth init incident --from-lockfiles good.txt bad.txt \
    --project project --test tests/test_features.py::test_clip_and_round \
    --python 3.11 --group pandas,pytz,tzdata
regressleuth diagnose incident/incident.yaml
```

Recorded result (Linux, Python 3.11): **`verified`: pandas**, after 4 isolation and 4 audit
replays (8 version mixes, each installed into its own cached virtual environment). The
first run downloads about 40 MB of wheels; the cached rerun takes about 12 s.

Why `--group pandas,pytz,tzdata`: pandas 3 no longer requires pytz and tzdata, so the bad
lockfile drops them. A mix that keeps pandas 2.3.3 but removes them cannot be installed.
Without the group, Regressleuth still names pandas, but as `inferred`: 8 of its 21 audit
checks would need such uninstallable mixes. `init` prints a hint when distributions
disappear.

The committed `incident/` folder is what `init` wrote. Environments go to
`incident/.regressleuth-envs/` (ignored by git).
