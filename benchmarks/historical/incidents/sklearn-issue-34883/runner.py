"""scikit-learn #34883: verbatim reproducer; pass iff the balanced forest fits on string labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert sklearn.__version__ == state["components"]["scikit-learn"]
    X = np.random.RandomState(0).rand(20, 5)
    y = np.array(["1"] * 10 + ["2"] * 10)
    try:
        RandomForestClassifier(n_estimators=5, class_weight="balanced").fit(X, y)
        metric = 1.0
    except ValueError:
        metric = 0.0
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
