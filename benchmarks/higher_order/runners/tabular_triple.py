"""Column order, a positional model, and a schema guard that reorders columns by name."""

import json

import joblib
import numpy as np
from ho_common import EXAMPLES, read_state, use_example, write_metric

use_example("real_tabular")
import runner as tab  # noqa: E402

state, result = read_state()
parts = state["components"]
model_dir = EXAMPLES / "real_tabular" / "artifacts" / "models" / parts["model"]
meta = json.loads((model_dir / "meta.json").read_text())
model = joblib.load(model_dir / "model.joblib")
cases = json.loads(open(state["cases"], encoding="utf-8").read())
canonical = meta["feature_names"]
order = sorted(canonical) if parts["column_order"] == "alphabetical" else list(canonical)
matrix = np.array([[c["features"][n] for n in order] for c in cases], dtype=float)
matrix = tab.snapshot(parts["data"], matrix, order)
if parts["schema_guard"] == "on" or meta["input"] == "by_name":
    matrix = matrix[:, [order.index(n) for n in canonical]]
threshold = float(parts["policy"].partition("-")[2])
labels = np.array([c["label"] for c in cases])
predicted = (model.predict_proba(matrix)[:, 1] >= threshold).astype(int)
write_metric(result, float(np.mean(predicted == labels)))
