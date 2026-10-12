"""scikit-learn #33032: verbatim reproducer; pass iff sklearn float32 residual <= 1.01 x scipy float32."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import sklearn
from scipy import linalg
from sklearn.linear_model import LinearRegression


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    assert sklearn.__version__ == state["components"]["scikit-learn"]

    np.random.seed(cases["seed"])
    n_samples = cases["n_samples"]
    x1 = np.random.rand(n_samples)
    x2 = 0.3 * x1 + 0.1 * np.random.rand(n_samples)
    X = np.column_stack([x1, x2])
    y = X @ [0.5, 2.0] + 0.1 * np.random.rand(n_samples)
    X32, y32 = X.astype(np.float32), y.astype(np.float32)
    scipy_f32 = linalg.lstsq(X32, y32)[0]
    sklearn_f32 = LinearRegression(fit_intercept=False).fit(X32, y32).coef_
    scipy_residue = float(linalg.norm(y32 - X32 @ scipy_f32))
    sklearn_residue = float(linalg.norm(y32 - X32 @ sklearn_f32))
    metric = float(sklearn_residue <= cases["tolerance_ratio"] * scipy_residue)
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
