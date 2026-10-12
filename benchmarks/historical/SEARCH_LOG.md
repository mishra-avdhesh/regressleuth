# Candidate search record

Search date: 2026-10-10 UTC. All 30 examined issue IDs were logged in
`CANDIDATES.jsonl` before any strategy evaluation. Search results were screened for
dated public reports and an apparent fixed reproducer; this was not a random sample of
all software regressions. No Regressleuth outcomes informed intake.

Sources and queries:

- Public web search for `pandas 2.2 regression 2.1`, `pandas 3.0 regression 2.3`,
  `numpy 2.0 regression 1.26`, `scikit-learn 1.6 regression 1.5`,
  `Pillow 10 ANTIALIAS 9.5`, and model/tokenizer, torchvision, MLflow regressions.
- GitHub issue search: `repo:pandas-dev/pandas is:issue label:Regression
  created:2025-01-01..2026-10-07`, sorted by creation descending, first page.
- GitHub issue search: `repo:scikit-learn/scikit-learn is:issue regression
  created:2024-01-01..2026-10-07`, sorted by creation descending, first page.
- Direct GitHub issue metadata was used to confirm source dates for issue IDs in the
  candidate log. The issue URL for every candidate is stored in that record.

The intake cap of 30 candidates is now reached. Further searches are outside this pilot.
