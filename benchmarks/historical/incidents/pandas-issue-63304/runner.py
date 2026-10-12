"""pandas #63304: verbatim reproducer; pass iff drop(index=[pd.NA]) succeeds and leaves 2 rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa  # noqa: F401 - imported by the public reproducer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    assert pd.__version__ == state["components"]["pandas"]
    try:
        df = pd.DataFrame(index=pd.Index([None, b"\xe3", b"\xe3"], dtype="binary[pyarrow]", name="bytes_col"))
        result = df.drop(index=[pd.NA])
        metric = float(len(result) == 2)
    except Exception:  # noqa: BLE001 - the reported regression is an exception here
        metric = 0.0
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
