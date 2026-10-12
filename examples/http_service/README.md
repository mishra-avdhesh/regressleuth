# HTTP service demo

A risk-scoring service (standard-library HTTP server + scikit-learn) runs as two releases:
`good` and `bad` (five components changed). Like a canary or feature-flag gateway, the service
accepts an `X-Regressleuth-Components` header that pins component versions per request, which
is all Regressleuth needs to replay hybrids over HTTP.

```bash
pip install -e ".[demo]"
python examples/http_service/prepare.py      # trains the two model versions, writes cases.jsonl
python examples/http_service/run_demo.py     # starts both releases, inspects, diagnoses, renders
```

Recorded run (2026-10-08): 5 changed components, 15 candidate causes, full exhaustive search
32 replays, budget 16. Diagnosis **verified under the configured replay model, assumptions,
and extended audit checks: `feature_assembler + model`** (a positional
gradient-boosting model meets a feature assembler that sorts columns) after 8 isolation
replays plus 13 extended-audit replays (21 in total), 1.6 s wall time. The HTML report is
written to `out/report.html`.
The saved JSON and HTML reports show the effective audit, interval, confidence, repeats,
and assumption checks.

To point it at your own service: implement version pinning from the header (or body), keep
the evaluation cases fixed, and set `base_url` in `incident.yaml`.
