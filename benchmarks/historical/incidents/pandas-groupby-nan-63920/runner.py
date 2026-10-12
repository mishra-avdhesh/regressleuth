"""Execute the fixed grouping test from pandas issue 63920."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    assert pd.__version__ == state["components"]["pandas"]

    frame = pd.DataFrame(
        {"metric": cases["metric"], "sector": cases["sector"]},
        index=pd.MultiIndex.from_arrays([cases["dates"], cases["companies"]], names=["dates", "company"]),
    )
    frame["sector"] = pd.Categorical(frame["sector"], categories=cases["categories"], ordered=True)
    grouped = frame.groupby(["dates", "sector"], observed=False)["metric"].sum()
    observed = float(grouped.loc[("2026-01-01", 2)])
    metric = float(observed == cases["expected_january_sector_2_sum"])
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
