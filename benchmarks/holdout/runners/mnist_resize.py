"""holdout_pillow_resize_default: a model trained on NEAREST-downsampled digits is served with
`Image.resize` and no explicit filter, which is BICUBIC since Pillow 7.0."""

import numpy as np
from common import DATA, load_json, read_state, write_metric
from PIL import Image

state, result = read_state()
parts = state["components"]
cases = load_json(state["cases"])
weights = load_json(DATA / "mnist" / f"{parts['model']}.json")
features = []
for case in cases:
    image = Image.fromarray(np.array(case["pixels"], dtype=np.uint8).reshape(28, 28))
    if parts["resize_call"] == "explicit-nearest":
        small = image.resize((14, 14), Image.Resampling.NEAREST)
    else:
        small = image.resize((14, 14))  # library default filter
    features.append(np.asarray(small, dtype=float).ravel() / 255.0)
logits = np.array(features) @ np.array(weights["coef"]).T + np.array(weights["intercept"])
labels = np.array([c["label"] for c in cases])
write_metric(result, float(np.mean(logits.argmax(axis=1) == labels)))
