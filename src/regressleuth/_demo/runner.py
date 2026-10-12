"""A tiny keyword sentiment classifier used by `regressleuth demo`.

It is pure standard-library Python so the demo runs anywhere. The pipeline has four
swappable parts; the incident changes all four, and only one *pair* of changes breaks it:
a tokenizer that stopped lowercasing and a notification step that now UPPERCASES text.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

POSITIVE = {"good", "great", "love", "excellent", "happy", "fun", "nice", "brilliant"}
NEGATIVE = {"bad", "awful", "hate", "terrible", "sad", "boring", "poor", "dull"}
EXTRA = {"wonderful": 1, "horrible": -1}  # lexicon v2 adds two words


def predict(components: dict[str, str], text: str) -> int:
    if components["normalizer"] == "shout":
        text = text.upper()
    tokens = re.findall(r"[A-Za-z']+", text)
    if components["tokenizer"] == "lowercase":
        tokens = [t.lower() for t in tokens]
    score = sum((t in POSITIVE) - (t in NEGATIVE) for t in tokens)
    if components["lexicon"] == "v2":
        score += sum(EXTRA.get(t, 0) for t in tokens)
    return int(score > 0) if components["threshold"] == "strict" else int(score >= 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    correct = sum(predict(state["components"], c["text"]) == c["label"] for c in cases)
    args.result.write_text(json.dumps({"metric": correct / len(cases)}), encoding="utf-8")


if __name__ == "__main__":
    main()
