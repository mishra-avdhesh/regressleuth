"""Replay runner for the real tabular demo (scikit-learn models on breast-cancer data).

Components: model (artifact directory), preprocessing (column order / external
standardization), policy (decision rule), data (feature-snapshot variant).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
PREPROCESSING = {"canonical-order", "alphabetical-order", "standardize-then-canonical"}


def snapshot(name: str, features: np.ndarray, columns: list[str]) -> np.ndarray:
    """Feature-store snapshot variants; each is a plausible upstream change."""
    if name == "snapshot-a":
        return features
    if name == "snapshot-b":  # float32 storage
        return features.astype(np.float32).astype(np.float64)
    out = features.copy()
    if name == "snapshot-c":  # upstream null filled with zero for the worst-* features
        out[:, [i for i, c in enumerate(columns) if c.startswith("worst")]] = 0.0
    elif name == "snapshot-d":  # area and perimeter reported in different units
        out[:, [i for i, c in enumerate(columns) if "area" in c or "perimeter" in c]] *= 0.001
    else:
        raise ValueError("unknown data snapshot")
    return out


def accuracy(state: dict) -> float:
    if state.get("metric") != "accuracy":
        raise ValueError("this runner supports only the accuracy metric")
    parts = state["components"]
    model_dir = ARTIFACTS / "models" / parts["model"]
    meta = json.loads((model_dir / "meta.json").read_text(encoding="utf-8"))
    model = joblib.load(model_dir / "model.joblib")
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    canonical = meta["feature_names"]
    if parts["preprocessing"] not in PREPROCESSING:
        raise ValueError("unknown preprocessing version")
    matrix = np.array([[c["features"][name] for name in canonical] for c in cases], dtype=float)
    matrix = snapshot(parts["data"], matrix, canonical)
    if parts["preprocessing"] == "standardize-then-canonical":
        stats = json.loads((ARTIFACTS / "scaler.json").read_text(encoding="utf-8"))
        matrix = (matrix - np.array(stats["mean"])) / np.array(stats["scale"])
    if meta.get("batch_standardize"):  # scale-invariant serving: z-score the inference batch
        matrix = (matrix - matrix.mean(axis=0)) / matrix.std(axis=0)
    order = list(canonical)
    if parts["preprocessing"] == "alphabetical-order":
        order = sorted(canonical)
        matrix = matrix[:, [canonical.index(name) for name in order]]
    if meta["input"] == "by_name":
        matrix = matrix[:, [order.index(name) for name in canonical]]
    probabilities = model.predict_proba(matrix)
    labels = np.array([case["label"] for case in cases])
    kind, _, value = parts["policy"].partition("-")
    threshold = float(value)
    if kind == "threshold":
        correct = (probabilities[:, 1] >= threshold).astype(int) == labels
    elif kind == "abstain":  # confidence below the threshold counts as a wrong answer
        correct = (probabilities.argmax(axis=1) == labels) & (probabilities.max(axis=1) >= threshold)
    else:
        raise ValueError("unknown policy")
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
