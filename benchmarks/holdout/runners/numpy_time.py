"""holdout_numpy2_float32_time: a time-delta feature computed with a stored scale factor.

`config_store` decides whether the scale factor is a NumPy float64 (JSON config) or float32
(columnar store). Under NumPy 2 (NEP 50) float32 * Python float stays float32, so epoch
timestamps lose ~128 s of precision; under NumPy 1 the result was promoted to float64.
"""

import numpy as np
from common import DATA, load_json, positive_probability, read_state, threshold_of, write_metric

state, result = read_state()
parts = state["components"]
cases = load_json(state["cases"])
weights = load_json(DATA / "numpy_time" / f"{parts['model']}.json")
scale = np.float32(1.0) if parts["config_store"] == "float32-parquet" else np.float64(1.0)
deltas = np.array([float(scale * c["event_ts"]) - float(scale * c["reset_ts"]) for c in cases])
features = np.column_stack([(deltas < 60).astype(float), deltas / 60.0,
                            np.array([c["log_amount"] for c in cases])])
features = (features - np.array(weights["mean"])) / np.array(weights["scale"])
predicted = positive_probability(weights, features) >= threshold_of(parts["policy"])
labels = np.array([c["label"] for c in cases])
write_metric(result, float(np.mean(predicted.astype(int) == labels)))
