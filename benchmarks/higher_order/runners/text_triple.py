"""Uncased DistilBERT behind three lowercasing safeguards.

Upper-cased text only hurts the uncased model if BOTH the explicit lowercase step is
switched off AND the tokenizer stops lowercasing. Also used, with the cased model, by the
`ctrl_text_lowercase_heals` control, where the lowercase step undoes a failing pair."""

import hashlib
import json

from ho_common import EXAMPLES, read_state, use_example, write_metric

use_example("real_text")
import runner as text  # noqa: E402

CACHE = EXAMPLES / "real_text" / "artifacts" / "cache_higher_order"

state, result = read_state()
parts = state["components"]
cases = json.loads(open(state["cases"], encoding="utf-8").read())
texts = [text.NORMALIZERS[parts["normalizer"]](c["text"]) for c in cases]
if parts["lowercase_step"] == "on":
    texts = [t.lower() for t in texts]
max_length = int(parts["max_length"])
key = hashlib.sha256(json.dumps([parts["model"], parts["normalizer"], parts["lowercase_step"],
                                 max_length, parts["tokenizer"], len(cases)]).encode()).hexdigest()[:24]
path = CACHE / f"{key}.json"
if path.exists():
    probabilities = json.loads(path.read_text())
else:
    probabilities = text.positive_probabilities(parts["model"], texts, max_length, parts["tokenizer"])
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(probabilities))
threshold = text.THRESHOLDS[parts["policy"]]
correct = sum(int(p >= threshold) == c["label"] for p, c in zip(probabilities, cases, strict=True))
write_metric(result, correct / len(cases))
