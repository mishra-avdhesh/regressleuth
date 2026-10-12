"""Sentinel imputation with defense in depth: chained assignment (silently a no-op on
pandas 3) is normally backed up by a downstream validator that re-imputes with .loc."""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from ho_common import EXAMPLES, read_state, write_metric

state, result = read_state()
parts = state["components"]
weights = json.loads((EXAMPLES / "real_env" / "artifacts" / f"{parts['model']}.json").read_text())
cases = json.loads(Path(state["cases"]).read_text())
frame = pd.DataFrame([c["features"] for c in cases])[weights["features"]]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for column, median in weights["medians"].items():
        if parts["imputation_code"] == "impute-loc":
            frame.loc[frame[column] == -999.0, column] = median
        else:
            frame[column][frame[column] == -999.0] = median  # noqa: PD008 - the bug under test
    if parts["validator"] == "on":
        for column, median in weights["medians"].items():
            frame.loc[frame[column] == -999.0, column] = median
z = (frame.to_numpy(dtype=float) - np.array(weights["mean"])) / np.array(weights["scale"])
probability = 1 / (1 + np.exp(-np.clip(z @ np.array(weights["coef"]) + weights["intercept"], -50, 50)))
threshold = float(parts["policy"].partition("-")[2])
labels = np.array([c["label"] for c in cases])
write_metric(result, float(np.mean((probability >= threshold).astype(int) == labels)))
