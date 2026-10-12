"""Replay runner for the image demo (8x8 digit images, scikit-learn classifiers).

Components: model (artifact), preprocessing (geometric / photometric transform),
data (sensor snapshot variant), policy (argmax or confidence-gated abstention).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def preprocess(name: str, x: np.ndarray) -> np.ndarray:
    images = x.reshape(-1, 8, 8)
    if name == "identity":
        out = images
    elif name == "transpose":  # axis order bug: height and width swapped
        out = images.transpose(0, 2, 1)
    elif name == "shift-1":  # one-pixel registration offset
        out = np.zeros_like(images)
        out[:, :, 1:] = images[:, :, :-1]
    elif name == "invert":  # polarity flipped
        out = 1.0 - images
    elif name == "blur":  # 3x3 box filter
        padded = np.pad(images, ((0, 0), (1, 1), (1, 1)), mode="edge")
        out = sum(padded[:, i : i + 8, j : j + 8] for i in range(3) for j in range(3)) / 9
    else:
        raise ValueError("unknown preprocessing")
    return out.reshape(-1, 64)


def snapshot(name: str, x: np.ndarray) -> np.ndarray:
    if name == "snapshot-a":
        return x
    if name == "snapshot-b":  # lower bit depth: 8 grey levels
        return np.floor(x * 8) / 8
    if name == "snapshot-c":  # 30% of sensor pixels dead (fixed mask)
        return x * (np.random.RandomState(0).rand(1, 64) > 0.3)
    raise ValueError("unknown data snapshot")


def accuracy(state: dict) -> float:
    if state.get("metric") != "accuracy":
        raise ValueError("this runner supports only the accuracy metric")
    parts = state["components"]
    model = joblib.load(ARTIFACTS / f"{parts['model']}.joblib")
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    pixels = np.array([case["pixels"] for case in cases], dtype=float) / 16.0
    features = preprocess(parts["preprocessing"], snapshot(parts["data"], pixels))
    labels = np.array([case["label"] for case in cases])
    probabilities = model.predict_proba(features)
    gate = float(parts["policy"].partition("-")[2])  # "abstain-0.30"
    correct = (probabilities.argmax(axis=1) == labels) & (probabilities.max(axis=1) >= gate)
    return float(np.mean(correct))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    args.result.write_text(json.dumps({"metric": accuracy(state)}), encoding="utf-8")


if __name__ == "__main__":
    main()
