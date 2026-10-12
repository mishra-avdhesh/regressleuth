"""Train the small real models and write the fixed evaluation cases for the tabular demo.

Everything is deterministic (fixed split and seeds) and written to ./artifacts,
which is git-ignored. Models are trusted local pickles produced by this script.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
EXTERNALLY_SCALED = {"lr_noscale", "lr_batchstd"}


def main() -> None:
    data = load_breast_cancer()
    names = [str(name) for name in data.feature_names]
    x_train, x_eval, y_train, y_eval = train_test_split(
        data.data, data.target, test_size=0.3, random_state=0, stratify=data.target
    )
    models = {
        "lr_v1": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)), "by_name"),
        "lr_v1b": (
            make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)),
            "by_name",
        ),
        "lr_underconf": (
            make_pipeline(StandardScaler(), LogisticRegression(C=0.002, max_iter=3000)),
            "by_name",
        ),
        "lr_noscale": (LogisticRegression(max_iter=3000), "by_name"),
        "lr_batchstd": (LogisticRegression(max_iter=3000), "by_name"),
        "gbm_v2": (GradientBoostingClassifier(random_state=0), "positional"),
        "gbm_v1b": (GradientBoostingClassifier(random_state=1, subsample=0.9), "positional"),
    }
    mean, scale = x_train.mean(axis=0), x_train.std(axis=0)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "scaler.json").write_text(
        json.dumps({"mean": mean.tolist(), "scale": scale.tolist()}), encoding="utf-8"
    )
    for name, (estimator, input_mode) in models.items():
        directory = ARTIFACTS / "models" / name
        directory.mkdir(parents=True, exist_ok=True)
        # lr_noscale expects externally standardized inputs (scaling lives in preprocessing)
        fit_x = (x_train - mean) / scale if name in EXTERNALLY_SCALED else x_train
        estimator.fit(fit_x, y_train)
        joblib.dump(estimator, directory / "model.joblib")
        (directory / "meta.json").write_text(
            json.dumps(
                {
                    "input": input_mode,
                    "feature_names": names,
                    "batch_standardize": name == "lr_batchstd",
                }
            ),
            encoding="utf-8",
        )
        eval_x = (x_eval - mean) / scale if name in EXTERNALLY_SCALED else x_eval
        accuracy = float(np.mean(estimator.predict(eval_x) == y_eval))
        print(f"{name}: clean accuracy {accuracy:.3f}")
    cases = [
        {
            "case_id": index,
            "features": {name: float(value) for name, value in zip(names, row, strict=True)},
            "label": int(label),
        }
        for index, (row, label) in enumerate(zip(x_eval, y_eval, strict=True))
    ]
    (HERE / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    print(f"wrote {len(cases)} fixed evaluation cases")


if __name__ == "__main__":
    main()
