"""scikit-learn #35038: verbatim reproducer; pass iff the star import succeeds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sklearn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert sklearn.__version__ == state["components"]["scikit-learn"]
    try:
        exec("from sklearn.model_selection import *", {})  # noqa: S102 - the reported statement
        metric = 1.0
    except ImportError:
        metric = 0.0
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
