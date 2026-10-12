"""Train the small image classifiers and write the fixed evaluation cases (scikit-learn digits).

Deterministic and offline: the 8x8 digit images ship with scikit-learn. Artifacts go to
./artifacts (git-ignored). Models are trusted local pickles produced by this script.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import load_digits
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"


def transpose(x: np.ndarray) -> np.ndarray:
    return x.reshape(-1, 8, 8).transpose(0, 2, 1).reshape(-1, 64)


def shift(x: np.ndarray) -> np.ndarray:
    images = x.reshape(-1, 8, 8)
    out = np.zeros_like(images)
    out[:, :, 1:] = images[:, :, :-1]
    return out.reshape(-1, 64)


def main() -> None:
    data = load_digits()
    x_train, x_eval, y_train, y_eval = train_test_split(
        data.data / 16.0, data.target, test_size=0.3, random_state=0, stratify=data.target
    )
    both = np.concatenate([y_train, y_train])
    models = {
        "lr_plain": (LogisticRegression(max_iter=3000), x_train, y_train),
        "lr_plain_b": (LogisticRegression(C=2.0, max_iter=3000), x_train, y_train),
        "lr_aug_transpose": (
            LogisticRegression(max_iter=3000),
            np.vstack([x_train, transpose(x_train)]),
            both,
        ),
        "lr_aug_shift": (
            LogisticRegression(max_iter=3000),
            np.vstack([x_train, shift(x_train)]),
            both,
        ),
        "mlp": (MLPClassifier((64,), max_iter=800, random_state=0), x_train, y_train),
    }
    ARTIFACTS.mkdir(exist_ok=True)
    for name, (model, features, labels) in models.items():
        model.fit(features, labels)
        joblib.dump(model, ARTIFACTS / f"{name}.joblib")
        print(f"{name}: clean accuracy {model.score(x_eval, y_eval):.3f}")
    cases = [
        {"case_id": i, "pixels": (row * 16).round(4).tolist(), "label": int(label)}
        for i, (row, label) in enumerate(zip(x_eval, y_eval, strict=True))
    ]
    (HERE / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    print(f"wrote {len(cases)} fixed evaluation cases")


if __name__ == "__main__":
    main()
