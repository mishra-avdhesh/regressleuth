"""holdout_csv_na_country_code: country codes round-trip through a CSV export and read_csv.

Alpha-3 exports write Namibia as NAM; alpha-2 exports write NA, which pandas' default
`na_values` turns into NaN unless the parser disables the default missing-value strings.
"""

import io

import numpy as np
import pandas as pd
from common import DATA, load_json, positive_probability, read_state, threshold_of, write_metric

ALPHA3 = {"US": "USA", "GB": "GBR", "DE": "DEU", "NA": "NAM", "IN": "IND", "BR": "BRA",
          "ZA": "ZAF", "KE": "KEN"}
ALPHA2 = {v: k for k, v in ALPHA3.items()}

state, result = read_state()
parts = state["components"]
cases = load_json(state["cases"])
weights = load_json(DATA / "csv_country" / f"{parts['model']}.json")
rows = ["case_id,country,amount"]
for c in cases:
    code = c["country"] if parts["export_format"] == "iso-alpha2" else ALPHA3[c["country"]]
    rows.append(f"{c['case_id']},{code},{c['amount']}")
text = "\n".join(rows) + "\n"
if parts["csv_parser"] == "explicit-na":
    frame = pd.read_csv(io.StringIO(text), keep_default_na=False, na_values=[""])
else:
    frame = pd.read_csv(io.StringIO(text))
countries = weights["countries"]
codes = [ALPHA2.get(v, v) if isinstance(v, str) else None for v in frame["country"]]
onehot = np.array([[1.0 if code == k else 0.0 for k in countries] for code in codes])
features = np.column_stack([onehot, np.log(frame["amount"].to_numpy(dtype=float))])
features = (features - np.array(weights["mean"])) / np.array(weights["scale"])
predicted = positive_probability(weights, features) >= threshold_of(parts["policy"])
labels = np.array([c["label"] for c in cases])
write_metric(result, float(np.mean(predicted.astype(int) == labels)))
