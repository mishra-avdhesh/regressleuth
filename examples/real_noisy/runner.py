"""Replay runner for the noisy-training demo: retrain a small network, then evaluate.

Each replay trains from scratch with the run `seed` (initialization, shuffling, the
label-noise draw and the training subsample all depend on it), so the metric is
genuinely stochastic. Evaluation always uses the same held-out cases and labels.

Components: train_data (full or a random subset), width (hidden units),
label_noise (fraction of training labels replaced at random), epochs (optimizer
iterations), eval_dtype (float precision of the evaluation features; a neutral decoy).
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier


def accuracy(state: dict) -> float:
    if state.get("metric") != "accuracy":
        raise ValueError("this runner supports only the accuracy metric")
    parts, seed = state["components"], int(state.get("seed", 0))
    data = load_digits()
    x_train, _, y_train, _ = train_test_split(
        data.data / 16.0, data.target, test_size=0.3, random_state=0, stratify=data.target
    )
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    x_eval = np.array([case["pixels"] for case in cases], dtype=float) / 16.0
    y_eval = np.array([case["label"] for case in cases])
    rng = np.random.RandomState(seed)
    labels = y_train.copy()
    noise = float(parts["label_noise"])
    if noise:
        flipped = rng.rand(len(labels)) < noise
        labels[flipped] = rng.randint(0, 10, flipped.sum())
    features = x_train
    if parts["train_data"] != "full":
        size = int(parts["train_data"].partition("-")[2])
        pick = rng.choice(len(features), size, replace=False)
        features, labels = features[pick], labels[pick]
    model = MLPClassifier(
        (int(parts["width"]),),
        max_iter=int(parts["epochs"]),
        learning_rate_init=0.001,
        random_state=seed,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(features, labels)
    if parts["eval_dtype"] == "float32":
        x_eval = x_eval.astype(np.float32).astype(float)
    return float(model.score(x_eval, y_eval))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    args.result.write_text(json.dumps({"metric": accuracy(state)}), encoding="utf-8")


if __name__ == "__main__":
    main()
