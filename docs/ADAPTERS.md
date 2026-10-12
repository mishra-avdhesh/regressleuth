# Adapters: how a hybrid gets evaluated

Every adapter implements one contract (`regressleuth.adapters.Adapter`): given the component
versions to use, a run seed, the metric name and the fixed cases, return **a finite metric**,
**incompatible** (this mix cannot be built), or **an error with a kind**. Adapters never retry
and never judge pass/fail, so budget accounting is identical whichever adapter you use.

| Error kind | Raised when |
|---|---|
| `timeout` | the replay exceeded `timeout_seconds` |
| `start_failed` | the command or container could not start |
| `nonzero_exit` | the process exited non-zero |
| `bad_output` | result missing, not JSON, wrong shape, wrong prediction count |
| `invalid_metric` | the metric is not a finite number |
| `missing_interpreter` | the interpreter mapped for an environment version does not exist |
| `connection`, `http_status` | the service is unreachable or answered 4xx/5xx |
| `adapter_unavailable` | a required tool or `${ENV}` variable is missing |
| `exception` | a Python callable raised (only the exception type is kept) |

Reports keep only the kind. `diagnose --diagnostics-dir DIR` writes each replay's stdout and
stderr tails (secret-looking strings redacted) to local files for debugging.

## `command`: a local program (default)

```yaml
adapter:
  type: command
  command: ["{python}", "runner.py", "--state", "{state}", "--result", "{result}"]
  cwd: .                       # relative to the incident file
  timeout_seconds: 600
  env: {API_TOKEN: "${API_TOKEN}"}   # values are expanded at run time, never written to reports
  inherit_env: true            # false keeps only PATH, HOME, LANG, TMPDIR...
  interpreters:                # optional: switch Python environments per component version
    component: environment
    map: {py312-pandas2: envs/pandas2/bin/python, py312-pandas3: envs/pandas3/bin/python}
```

Placeholders: `{python}` (current interpreter, or the mapped one), `{state}`, `{result}`,
`{cases}`, `{seed}`. The state file is `{"components": {...}, "cases": "<abs path>",
"metric": "...", "seed": n}`; the runner writes `{"metric": x}` or `{"status": "incompatible"}`.
No shell is used. Environment switching via `interpreters` gives real isolation of Python
dependencies (separate virtualenvs); it does not isolate system libraries, drivers or hardware.

## `python`: an in-process function

```yaml
adapter: {type: python, callable: "my_pipeline:evaluate", path: ., timeout_seconds: 300}
```

`evaluate(components, seed=..., cases=...)` returns the metric (`seed` and `cases` are passed
only if the function accepts them). Raise `regressleuth.errors.IncompatibleReplay` for an
unbuildable mix. The timeout is best effort: Python cannot stop a running thread. In code,
`regressleuth.diagnose(good, bad, run)` uses this adapter without any file.

## `http`: a running service

```yaml
cases: cases.jsonl             # {"input": ..., "label": ...} per line
adapter:
  type: http
  base_url: ${SERVICE_URL}     # http(s) only
  mode: predict                # predict: score locally; evaluate: the service returns {"metric": x}
  path: /predict
  components_via: header       # header (X-Regressleuth-Components: JSON) or body
  batch_size: 64
  headers: {Authorization: "Bearer ${SERVICE_TOKEN}"}
  timeout_seconds: 30
```

The service must be able to serve a requested mix of versions for one request, as canary
or feature-flag routers do. `predict` posts `{"instances": [...]}` and expects
`{"predictions": [...]}`; `evaluate` posts `{"components", "seed", "metric"}`. HTTP 409/422
with `{"status": "incompatible"}` marks an unbuildable mix. See the
[service demo](../examples/http_service).

## `docker`: a container per replay (experimental)

```yaml
adapter:
  type: docker
  command: ["python", "/app/runner.py", "{state}", "{result}"]
  images: {component: environment, map: {pandas2: "myimg:pandas2", pandas3: "myimg:pandas3"}}
  network: none
```

Runs `docker run --rm --network none` with the work directory mounted at `/regressleuth/work`
and the cases read-only at `/regressleuth/cases`. **Status: experimental.** Docker was not
available on the machine this release was built on, so the adapter is tested only against a
fake `docker` executable that checks the command line and emulates the container; it has not
been validated against a real Docker daemon. Use the `command` adapter with `interpreters`
for tested environment isolation.

## Writing your own

Subclass `Adapter`, implement `replay(request) -> ReplayOutcome` and `describe()` (no secret
values), and pass an instance as `investigate(incident, executor=adapter)`.
