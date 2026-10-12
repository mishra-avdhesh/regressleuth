"""Replay runner for the environment-version demo. Needs only pandas and numpy.

Components: model (JSON weights), preprocessing (sentinel imputation code),
environment (selects the interpreter, see the incident's `interpreters` map),
policy (decision threshold).

`impute-loc` is the supported way to fix sentinel values. `impute-chained` uses
chained assignment, which works on pandas 2.x and silently does nothing on pandas 3.x.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
SENTINEL = -999.0


def impute(frame: pd.DataFrame, method: str, medians: dict[str, float]) -> pd.DataFrame:
    for column, median in medians.items():
        if method == "impute-loc":
            frame.loc[frame[column] == SENTINEL, column] = median
        elif method == "impute-chained":
            frame[column][frame[column] == SENTINEL] = median
        else:
            raise ValueError("unknown preprocessing")
    return frame


def evaluate(state: dict) -> dict:
    parts = state["components"]
    weights = json.loads((ARTIFACTS / f"{parts['model']}.json").read_text(encoding="utf-8"))
    major = int(pd.__version__.split(".")[0])
    if major < weights["requires_pandas_major"]:
        return {"status": "incompatible"}
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    frame = pd.DataFrame([case["features"] for case in cases])[weights["features"]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        frame = impute(frame, parts["preprocessing"], weights["medians"])
    z = (frame.to_numpy(dtype=float) - np.array(weights["mean"])) / np.array(weights["scale"])
    logits = z @ np.array(weights["coef"]) + weights["intercept"]
    probability = 1.0 / (1.0 + np.exp(-np.clip(logits, -50, 50)))
    threshold = float(parts["policy"].partition("-")[2])
    labels = np.array([case["label"] for case in cases])
    return {"metric": float(np.mean((probability >= threshold).astype(int) == labels))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    args.result.write_text(json.dumps(evaluate(state)), encoding="utf-8")


if __name__ == "__main__":
    main()
