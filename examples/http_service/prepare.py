"""Train the two model versions the demo service can serve and write the fixed cases."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent


def main() -> None:
    data = load_breast_cancer()
    names = [str(n) for n in data.feature_names]
    x_train, x_eval, y_train, y_eval = train_test_split(
        data.data, data.target, test_size=0.3, random_state=7, stratify=data.target
    )
    artifacts = HERE / "artifacts"
    artifacts.mkdir(exist_ok=True)
    registry = {
        "risk-model:v1": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)), "by_name"),
        "risk-model:v2": (GradientBoostingClassifier(random_state=0), "positional"),
    }
    for version, (model, contract) in registry.items():
        model.fit(x_train, y_train)
        joblib.dump(model, artifacts / f"{version.replace(':', '_')}.joblib")
        (artifacts / f"{version.replace(':', '_')}.json").write_text(
            json.dumps({"input": contract, "feature_names": names}), encoding="utf-8"
        )
        print(f"{version}: clean accuracy {model.score(x_eval, y_eval):.3f}")
    with (HERE / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for row, label in zip(x_eval, y_eval, strict=True):
            handle.write(
                json.dumps({"input": dict(zip(names, map(float, row), strict=True)), "label": int(label)})
                + "\n"
            )
    print(f"wrote {len(y_eval)} fixed evaluation cases")


if __name__ == "__main__":
    main()
