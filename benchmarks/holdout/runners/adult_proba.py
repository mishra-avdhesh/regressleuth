"""holdout_proba_column_order: reading predict_proba by a hard-coded column index.

Column order follows the sorted class labels. A retrained model whose labels were renamed
puts the positive class in a different column."""

import numpy as np
from common import DATA, load_json, positive_probability, read_state, threshold_of, write_metric

POSITIVE = {"yes", "high_income"}

state, result = read_state()
parts = state["components"]
cases = load_json(state["cases"])
weights = load_json(DATA / "adult" / f"proba_{parts['model']}.json")
rows = []
for case in cases:
    encoded = []
    for column in weights["categorical"]:
        encoded.extend(1.0 if case[column] == v else 0.0 for v in weights["categories"][column])
    rows.append(encoded + [case[n] for n in weights["numeric"]])
features = (np.array(rows) - np.array(weights["mean"])) / np.array(weights["scale"])
p_second = positive_probability(weights, features)  # probability of classes[1]
proba = np.column_stack([1 - p_second, p_second])
if parts["postprocessing"] == "lookup-by-name":
    column = next(i for i, name in enumerate(weights["classes"]) if name in POSITIVE)
else:
    column = 1
predicted = proba[:, column] >= threshold_of(parts["policy"])
labels = np.array([c["label"] for c in cases])
write_metric(result, float(np.mean(predicted.astype(int) == labels)))
