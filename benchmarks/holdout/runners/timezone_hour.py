"""holdout_timezone_hour_feature: hour-of-day from timestamps exported as local naive times or
as UTC ISO strings, read with or without converting to the business time zone."""

import numpy as np
import pandas as pd
from common import DATA, load_json, positive_probability, read_state, threshold_of, write_metric

ZONE = "America/New_York"

state, result = read_state()
parts = state["components"]
frame = pd.DataFrame(load_json(state["cases"]))
weights = load_json(DATA / "timezone" / f"{parts['model']}.json")
column = frame["local_naive"] if parts["export_format"] == "local-naive" else frame["utc_iso"]
stamps = pd.to_datetime(column)
if parts["preprocessing"] == "tz-aware" and stamps.dt.tz is not None:
    stamps = stamps.dt.tz_convert(ZONE)
hours = stamps.dt.hour.to_numpy()
onehot = np.eye(24)[hours]
features = np.column_stack([onehot, frame["log_amount"].to_numpy()])
features = (features - np.array(weights["mean"])) / np.array(weights["scale"])
predicted = positive_probability(weights, features) >= threshold_of(parts["policy"])
write_metric(result, float(np.mean(predicted.astype(int) == frame["label"].to_numpy())))
