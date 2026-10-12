"""pandas #65118: verbatim reproducer; pass iff df['prices'] is divided by 100."""

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
    cols = pd.MultiIndex.from_tuples(
        [("info", "M"), ("info", 0), ("earnings", 1), ("earnings", 2), ("prices", 0)]
    )
    df = pd.DataFrame(np.arange(20, dtype=float).reshape(4, 5), columns=cols)
    df["earnings"] = df["earnings"] / 100
    df["prices"] = df["prices"] / 100
    metric = float(np.allclose(df[("prices", 0)].to_numpy(), cases["expected_prices"]))
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
