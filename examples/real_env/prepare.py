"""Write numpy-only model weights and fixed evaluation cases for the environment demo.

Cases carry upstream sentinel values (-999 for missing) in two features, so the
imputation step in preprocessing matters. Run with any interpreter that has scikit-learn.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

HERE = Path(__file__).resolve().parent
SENTINEL_COLUMNS = ["mean radius", "worst area", "mean texture", "worst perimeter"]


def main() -> None:
    data = load_breast_cancer()
    names = [str(n) for n in data.feature_names]
    x_train, x_eval, y_train, y_eval = train_test_split(
        data.data, data.target, test_size=0.3, random_state=0, stratify=data.target
    )
    mean, scale = x_train.mean(axis=0), x_train.std(axis=0)
    medians = {c: float(np.median(x_train[:, names.index(c)])) for c in SENTINEL_COLUMNS}
    out = HERE / "artifacts"
    out.mkdir(exist_ok=True)
    for name, c_value, requires in (("m1", 1.0, 0), ("m2", 0.5, 0), ("m3", 1.0, 3)):
        model = LogisticRegression(C=c_value, max_iter=3000).fit((x_train - mean) / scale, y_train)
        (out / f"{name}.json").write_text(
            json.dumps(
                {
                    "features": names,
                    "mean": mean.tolist(),
                    "scale": scale.tolist(),
                    "coef": model.coef_[0].tolist(),
                    "intercept": float(model.intercept_[0]),
                    "medians": medians,
                    "requires_pandas_major": requires,
                }
            ),
            encoding="utf-8",
        )
    rng = np.random.RandomState(0)
    cases = []
    for i, (row, label) in enumerate(zip(x_eval, y_eval, strict=True)):
        features = {n: float(v) for n, v in zip(names, row, strict=True)}
        if rng.rand() < 0.4:  # upstream null encoded as a sentinel
            for column in SENTINEL_COLUMNS:
                features[column] = -999.0
        cases.append({"case_id": i, "features": features, "label": int(label)})
    (HERE / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    print(
        f"wrote {len(cases)} fixed evaluation cases; sentinel rows: "
        f"{sum(c['features'][SENTINEL_COLUMNS[0]] == -999.0 for c in cases)}"
    )


if __name__ == "__main__":
    main()
