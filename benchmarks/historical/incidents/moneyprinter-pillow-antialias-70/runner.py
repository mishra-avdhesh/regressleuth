"""Minimal execution of the Pillow resize call reported in MoneyPrinterTurbo #70."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import PIL
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    assert PIL.__version__ == state["components"]["pillow"]

    width, height = cases["input_rgb_size"]
    image = Image.new("RGB", (width, height), color="white")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = image.resize(
                (int(image.size[0] * (cases["output_height"] / image.size[1])), cases["output_height"]),
                Image.ANTIALIAS,
            ).convert("L")
    except AttributeError as exc:
        if "ANTIALIAS" not in str(exc):
            raise
        metric = 0.0
    else:
        metric = float(
            list(result.size) == cases["expected_output_size"]
            and result.mode == cases["expected_output_mode"]
        )
    args.result.write_text(json.dumps({"metric": metric}), encoding="utf-8")


if __name__ == "__main__":
    main()
