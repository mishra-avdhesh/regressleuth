"""pandas #57859: run the verbatim public reproducer; pass iff print(df.head()) succeeds."""

from __future__ import annotations

import argparse
import contextlib
import io
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
    source = (Path(__file__).parent / cases["reproducer"]).read_text(encoding="utf-8")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, cases["reproducer"], "exec"), {"__name__": "__reproducer__"})  # noqa: S102
    except Exception:  # noqa: BLE001 - any exception at the reported call is the regression
        metric = 0.0
    else:
        metric = 1.0
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
