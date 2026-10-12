"""Deterministic churn classifier for counterfactual replay examples.

The input state contains a component selection, an absolute cohort path, and
the requested metric. The output is a JSON object with a literal metric key.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

MODEL_BIAS = {"linear-v1": 0.0, "linear-v2": 0.06}
PREPROCESSING_BIAS = {
    "risk-score-v1": 0.0,
    "risk-score-corrected": -0.01,
    "risk-score-upshift": 0.06,
}
POLICY_THRESHOLD = {"balanced": 0.50, "growth": 0.39, "conservative": 0.51}


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def accuracy(state: dict[str, Any]) -> float:
    if state.get("metric") != "accuracy":
        raise ValueError("this runner supports only the accuracy metric")
    components = state.get("components")
    if not isinstance(components, dict) or set(components) != {"model", "preprocessing", "policy"}:
        raise ValueError("components must select model, preprocessing, and policy")
    try:
        model_bias = MODEL_BIAS[components["model"]]
        preprocessing_bias = PREPROCESSING_BIAS[components["preprocessing"]]
        threshold = POLICY_THRESHOLD[components["policy"]]
    except (KeyError, TypeError) as exc:
        raise ValueError("unknown component version") from exc

    cases_path = state.get("cases")
    if not isinstance(cases_path, str) or not Path(cases_path).is_absolute():
        raise ValueError("cases must be an absolute path")
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases must be a nonempty JSON array")

    seen_ids: set[str] = set()
    correct = 0
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be a JSON object")
        case_id = case.get("id")
        risk_score = case.get("risk_score")
        label = case.get("label")
        if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
            raise ValueError("case ids must be nonempty and unique")
        seen_ids.add(case_id)
        if (
            isinstance(risk_score, bool)
            or not isinstance(risk_score, (int, float))
            or not math.isfinite(risk_score)
            or not 0 <= risk_score <= 1
        ):
            raise ValueError(f"invalid risk_score for {case_id}")
        if type(label) is not int or label not in (0, 1):
            raise ValueError(f"invalid label for {case_id}")
        prediction = int(risk_score + preprocessing_bias + model_bias >= threshold)
        correct += prediction == label
    return correct / len(cases)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    score = accuracy(_load_object(args.state))
    args.result.write_text(json.dumps({"metric": score}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
