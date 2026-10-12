# Churn replay example

This small, deterministic classifier demonstrates counterfactual replay with a
fixed labeled cohort. Each account has a precomputed churn risk score and a
binary label. The runner applies the selected preprocessing offset, model
calibration, and decision policy, then reports classification accuracy.

The 20 accounts in `cases.json` are reused unchanged in every replay. The
example is a controlled diagnostic fixture, not a trained churn model or a
claim about real customer behavior.

The two incidents in `../../benchmarks/incidents/` show distinct failure modes:

| Incident | Regression mechanism | Minimal cause |
| --- | --- | --- |
| `churn_policy_threshold` | A lower decision threshold labels several stable accounts as churn risks. | `policy` |
| `churn_calibration_interaction` | The new model and new preprocessing each shift risk scores by 0.06. Either shift alone is safe on this cohort; together they cross the boundary. | `model` + `preprocessing` |

Run `python3 benchmarks/validate_fixtures.py` from the repository root to replay
all component combinations and compare them with `benchmarks/ground_truth.json`.
