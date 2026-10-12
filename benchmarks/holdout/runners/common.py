"""Shared helpers for holdout runners: state/result files and numpy-only models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

HOLDOUT = Path(__file__).resolve().parents[1]
DATA = HOLDOUT / "data"


def read_state() -> tuple[dict[str, Any], Path]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    return json.loads(args.state.read_text(encoding="utf-8")), args.result


def write_metric(path: Path | str, value: float) -> None:
    Path(path).write_text(json.dumps({"metric": float(value)}), encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def positive_probability(weights: dict[str, Any], features: np.ndarray) -> np.ndarray:
    logits = features @ np.asarray(weights["coef"], dtype=float) + float(weights["intercept"])
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -50, 50)))


def threshold_of(policy: str) -> float:
    return float(policy.partition("-")[2])
