"""holdout_pythonhashseed_hashing: hashing-trick features built with Python's builtin hash().

The runtime manifest decides the serving process's environment. The training job fixed
PYTHONHASHSEED=0; a manifest without it gets a fresh random salt in every process."""

import json
import os
import subprocess
import sys

MANIFESTS = {"manifest-v1": {"PYTHONHASHSEED": "0"}, "manifest-v2": {}}
BUCKETS = 512


def featurize(cases, weights):
    import numpy as np

    rows = []
    for case in cases:
        vector = [0.0] * BUCKETS
        for column in weights["categorical"]:
            vector[hash(f"{column}={case[column]}") % BUCKETS] += 1.0
        rows.append(vector + [case[n] for n in weights["numeric"]])
    return np.array(rows, dtype=float)


def serve(state_path, result_path):
    import numpy as np
    from common import DATA, load_json, positive_probability, threshold_of, write_metric

    state = load_json(state_path)
    parts = state["components"]
    cases = load_json(state["cases"])
    weights = load_json(DATA / "adult" / f"hashing_{parts['model']}.json")
    features = (featurize(cases, weights) - np.array(weights["mean"])) / np.array(weights["scale"])
    predicted = positive_probability(weights, features) >= threshold_of(parts["policy"])
    labels = np.array([c["label"] for c in cases])
    write_metric(result_path, float(np.mean(predicted.astype(int) == labels)))


if __name__ == "__main__":
    if sys.argv[1] == "--serve":
        serve(sys.argv[2], sys.argv[3])
    else:
        state_path, result_path = sys.argv[2], sys.argv[4]
        manifest = json.load(open(state_path))["components"]["runtime_env"]
        env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
        env.update(MANIFESTS[manifest])
        subprocess.run([sys.executable, __file__, "--serve", state_path, result_path], env=env,
                       check=True)
