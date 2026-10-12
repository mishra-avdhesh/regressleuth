"""pandas #66341: documentation example; pass iff str.split on a categorical returns lists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    assert pd.__version__ == state["components"]["pandas"]
    s = pd.Series(["this is a regular sentence", "https://docs.python.org/3/tutorial/index.html", np.nan])
    first = s.astype("category").str.split().iloc[0]
    metric = float(isinstance(first, list) and first == cases["expected_first"])
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
