"""holdout_encoder_refit_per_batch: categorical codes from a training-fitted encoder versus an
encoder refit on every serving batch (training-serving skew)."""

import numpy as np
from common import DATA, load_json, positive_probability, read_state, threshold_of, write_metric

state, result = read_state()
parts = state["components"]
cases = load_json(state["cases"])
weights = load_json(DATA / "adult" / f"encoder_{parts['model']}.json")
columns, trained = weights["categorical"], weights["categories"]
size = len(cases) if parts["batch_size"] == "full" else int(parts["batch_size"])
rows = []
for start in range(0, len(cases), size):
    batch = cases[start : start + size]
    if parts["encoder_fit"] == "refit-per-batch":
        vocabularies = {column: sorted({c[column] for c in batch}) for column in columns}
    else:
        vocabularies = trained
    lookup = {column: {v: i for i, v in enumerate(vocabularies[column])} for column in columns}
    for case in batch:
        encoded = []
        for column in columns:
            code = lookup[column].get(case[column], -1)
            one = [0.0] * len(trained[column])
            if 0 <= code < len(one):
                one[code] = 1.0
            encoded.extend(one)
        rows.append(encoded + [case[n] for n in weights["numeric"]])
features = np.array(rows, dtype=float)
features = (features - np.array(weights["mean"])) / np.array(weights["scale"])
predicted = positive_probability(weights, features) >= threshold_of(parts["policy"])
labels = np.array([c["label"] for c in cases])
write_metric(result, float(np.mean(predicted.astype(int) == labels)))
