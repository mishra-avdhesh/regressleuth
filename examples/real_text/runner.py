"""Replay runner for the real text demo (Hugging Face SST-2 classifiers).

Components: model (Hub repo id), preprocessing (text normalizer), max_length
(tokenizer truncation), policy (positive-class decision threshold). Model
probabilities are cached on disk per (model, preprocessing, max_length) so
repeated replays stay cheap; this does not change any measured value.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "artifacts" / "cache"
NORMALIZERS = {
    "identity": lambda text: text,
    "uppercase": lambda text: text.upper(),
    "strip-punctuation": lambda text: "".join(c for c in text if c.isalnum() or c.isspace()),
}
THRESHOLDS = {"threshold-0.50": 0.50, "threshold-0.60": 0.60}


def positive_probabilities(
    model_id: str, texts: list[str], max_length: int, tokenizer_mode: str
) -> list[float]:
    import torch
    from tokenizers import normalizers
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer_mode == "no-lowercasing":  # a misconfigured tokenizer: do_lower_case=False
        tokenizer.backend_tokenizer.normalizer = normalizers.BertNormalizer(
            clean_text=True, handle_chinese_chars=True, strip_accents=False, lowercase=False
        )
    elif tokenizer_mode != "lowercasing":
        raise ValueError("unknown tokenizer mode")
    model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()
    positive_index = 1
    for index, label in model.config.id2label.items():
        if str(label).upper().startswith("POS"):
            positive_index = int(index)
    probabilities: list[float] = []
    with torch.no_grad():
        for start in range(0, len(texts), 32):
            batch = tokenizer(
                texts[start : start + 32],
                truncation=True,
                max_length=max_length,
                padding=True,
                return_tensors="pt",
            )
            scores = torch.softmax(model(**batch).logits, dim=-1)[:, positive_index]
            probabilities.extend(float(value) for value in scores)
    return probabilities


def accuracy(state: dict) -> float:
    if state.get("metric") != "accuracy":
        raise ValueError("this runner supports only the accuracy metric")
    parts = state["components"]
    cases = json.loads(Path(state["cases"]).read_text(encoding="utf-8"))
    normalize = NORMALIZERS[parts["preprocessing"]]
    max_length = int(parts["max_length"])
    tokenizer_mode = parts.get("tokenizer", "lowercasing")
    key = hashlib.sha256(
        json.dumps([parts["model"], parts["preprocessing"], max_length, tokenizer_mode, len(cases)]).encode()
    ).hexdigest()[:24]
    cache_file = CACHE / f"{key}.json"
    if cache_file.is_file():
        probabilities = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        probabilities = positive_probabilities(
            parts["model"], [normalize(case["text"]) for case in cases], max_length, tokenizer_mode
        )
        CACHE.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(probabilities), encoding="utf-8")
    threshold = THRESHOLDS[parts["policy"]]
    correct = sum(
        int(probability >= threshold) == case["label"]
        for probability, case in zip(probabilities, cases, strict=True)
    )
    return correct / len(cases)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    args.result.write_text(json.dumps({"metric": accuracy(state)}), encoding="utf-8")


if __name__ == "__main__":
    main()
