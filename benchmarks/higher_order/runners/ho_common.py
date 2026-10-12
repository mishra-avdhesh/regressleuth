"""State/result helpers shared by the higher-order runners."""

import argparse
import json
import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[3] / "examples"


def read_state():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    return json.loads(args.state.read_text(encoding="utf-8")), args.result


def write_metric(path, value):
    Path(path).write_text(json.dumps({"metric": float(value)}), encoding="utf-8")


def use_example(name):
    sys.path.insert(0, str(EXAMPLES / name))
