"""holdout_pandas3_datetime_epoch: account age from `to_datetime(...).astype("int64") // 10**9`.

The idiom assumes nanosecond resolution. pandas 3 infers microseconds when parsing strings,
so the "epoch seconds" become epoch milliseconds / 1000 and account ages explode.
"""

import numpy as np
import pandas as pd
from common import DATA, load_json, positive_probability, read_state, threshold_of, write_metric

state, result = read_state()
parts = state["components"]
frame = pd.DataFrame(load_json(state["cases"]))
weights = load_json(DATA / "pandas_datetime" / f"{parts['model']}.json")
signup_epoch = pd.to_datetime(frame["signup"]).astype("int64") // 10**9
age_days = (frame["event_epoch"] - signup_epoch).clip(lower=0) / 86400.0
features = np.column_stack([np.log1p(age_days.to_numpy(dtype=float)), frame["log_amount"].to_numpy()])
features = (features - np.array(weights["mean"])) / np.array(weights["scale"])
predicted = positive_probability(weights, features) >= threshold_of(parts["policy"])
write_metric(result, float(np.mean(predicted.astype(int) == frame["label"].to_numpy())))
