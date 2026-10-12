"""Digit classifier: a sensor that delivers transposed images, an orientation-fix step in
preprocessing, and a model that was (or was not) trained with transposed augmentation."""

import joblib
import numpy as np
from ho_common import EXAMPLES, read_state, use_example, write_metric

use_example("real_image")
import runner as image  # noqa: E402

state, result = read_state()
parts = state["components"]
cases = __import__("json").loads(open(state["cases"], encoding="utf-8").read())
pixels = np.array([c["pixels"] for c in cases], dtype=float) / 16.0
pixels = image.snapshot(parts["data"], pixels)
if parts["sensor_orientation"] == "transposed":
    pixels = image.preprocess("transpose", pixels)
if parts["orientation_fix"] == "on" and parts["sensor_orientation"] == "transposed":
    pixels = image.preprocess("transpose", pixels)  # the fix knows the sensor metadata
model = joblib.load(EXAMPLES / "real_image" / "artifacts" / f"{parts['model']}.joblib")
probabilities = model.predict_proba(pixels)
gate = float(parts["policy"].partition("-")[2])
labels = np.array([c["label"] for c in cases])
correct = (probabilities.argmax(axis=1) == labels) & (probabilities.max(axis=1) >= gate)
write_metric(result, float(np.mean(correct)))
