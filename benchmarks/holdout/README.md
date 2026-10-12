# Holdout benchmark

Seven incidents reconstructed from documented, citable behavior, plus one control. Read
[`PREREGISTRATION.md`](PREREGISTRATION.md) first: it fixed the rules before any data existed and
logs every construction change. The suite is sealed (`SEAL.json`); `python benchmarks/seal.py
verify benchmarks/holdout` fails if any sealed file changed. Each incident cites its sources in
`metadata.provenance`. Results: [docs/BENCHMARKS.md](../../docs/BENCHMARKS.md).

```bash
python benchmarks/holdout/setup_envs.py     # NumPy 1/2 and pandas 2/3 interpreters (network once)
python benchmarks/holdout/prepare.py        # Adult and MNIST downloads, synthetic data, models
python benchmarks/prove_ground_truth.py benchmarks/holdout
python benchmarks/evaluate.py holdout
```
