"""Single source of truth for the real-model incident manifests and their ground truth.

Run `python benchmarks/build_incidents.py` to rewrite benchmarks/incidents/*.json
(except the static churn_* fixtures), benchmarks/controls/*.json and the ground-truth
files. `validate_fixtures.py` then proves each ground truth by replaying every
component combination, so the answers here are claims that get checked, not assumed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
UNCASED = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
CASED = "gchhablani/bert-base-cased-finetuned-sst2"


def replay(runner: str, cases: str, timeout: float = 120, **extra: Any) -> dict[str, Any]:
    return {
        "command": [
            "{python}",
            f"../../examples/{runner}/runner.py",
            "--state",
            "{state}",
            "--result",
            "{result}",
        ],
        "cases": f"../../examples/{runner}/{cases}",
        "metric": "accuracy",
        "direction": "higher",
        "regression_threshold": 0.1,
        "timeout_seconds": timeout,
        **extra,
    }


TAB = replay("real_tabular", "cases.json", 60)
TXT = replay("real_text", "cases.json", 600)

# id -> (good, bad, ground-truth cause, replay spec, family)
INCIDENTS: dict[str, tuple[dict[str, str], dict[str, str], list[str], dict[str, Any]]] = {}
# id -> (good, bad, expected status, replay spec): honesty controls on real models
CONTROLS: dict[str, tuple[dict[str, str], dict[str, str], str, dict[str, Any]]] = {}


def tab(model: str, prep: str, policy: str, data: str) -> dict[str, str]:
    return {"model": model, "preprocessing": prep, "policy": policy, "data": data}


# ---- tabular (scikit-learn, breast-cancer data) ------------------------------------------
INCIDENTS["tabular_model_x_column_order"] = (
    tab("lr_v1", "canonical-order", "threshold-0.50", "snapshot-a"),
    tab("gbm_v2", "alphabetical-order", "threshold-0.45", "snapshot-b"),
    ["model", "preprocessing"],
    TAB,
)
INCIDENTS["tabular_column_order"] = (
    tab("gbm_v1b", "canonical-order", "threshold-0.50", "snapshot-a"),
    tab("gbm_v2", "alphabetical-order", "threshold-0.45", "snapshot-b"),
    ["preprocessing"],
    TAB,
)
INCIDENTS["tabular_threshold"] = (
    tab("lr_v1", "canonical-order", "threshold-0.50", "snapshot-a"),
    tab("lr_v1b", "canonical-order", "threshold-0.99", "snapshot-b"),
    ["policy"],
    TAB,
)
INCIDENTS["tabular_calibration_x_abstain"] = (
    tab("lr_v1", "canonical-order", "abstain-0.50", "snapshot-a"),
    tab("lr_underconf", "canonical-order", "abstain-0.70", "snapshot-b"),
    ["model", "policy"],
    TAB,
)
INCIDENTS["tabular_units_x_model"] = (
    tab("lr_batchstd", "canonical-order", "threshold-0.50", "snapshot-a"),
    tab("lr_v1", "canonical-order", "threshold-0.45", "snapshot-d"),
    ["model", "data"],
    TAB,
)
INCIDENTS["tabular_upstream_zero_fill"] = (
    tab("lr_v1", "canonical-order", "threshold-0.50", "snapshot-a"),
    tab("lr_v1b", "canonical-order", "threshold-0.45", "snapshot-c"),
    ["data"],
    TAB,
)
CONTROLS["ctrl_tabular_coupled_scaling"] = (
    tab("lr_v1", "canonical-order", "threshold-0.50", "snapshot-a"),
    tab("lr_noscale", "standardize-then-canonical", "threshold-0.50", "snapshot-a"),
    "invalid_baseline",
    TAB,
)


# ---- text (Hugging Face SST-2 classifiers) -------------------------------------------------
def txt(model: str, prep: str, length: str, policy: str, tokenizer: str = "lowercasing") -> dict[str, str]:
    return {
        "model": model,
        "preprocessing": prep,
        "max_length": length,
        "policy": policy,
        "tokenizer": tokenizer,
    }


INCIDENTS["text_model_x_uppercase"] = (
    txt(UNCASED, "identity", "128", "threshold-0.50"),
    txt(CASED, "uppercase", "64", "threshold-0.60"),
    ["model", "preprocessing"],
    TXT,
)
INCIDENTS["text_uppercase_cased"] = (
    txt(CASED, "identity", "128", "threshold-0.50"),
    txt(CASED, "uppercase", "64", "threshold-0.60"),
    ["preprocessing"],
    TXT,
)
INCIDENTS["text_tokenizer_x_uppercase"] = (
    txt(UNCASED, "identity", "128", "threshold-0.50", "lowercasing"),
    txt(UNCASED, "uppercase", "64", "threshold-0.60", "no-lowercasing"),
    ["preprocessing", "tokenizer"],
    TXT,
)
INCIDENTS["text_truncation"] = (
    txt(UNCASED, "identity", "128", "threshold-0.50"),
    txt(UNCASED, "strip-punctuation", "6", "threshold-0.60"),
    ["max_length"],
    TXT,
)


# ---- image (scikit-learn digits, 8x8 images) ------------------------------------------------
IMG = replay("real_image", "cases.json", 60)


def img(model: str, prep: str, data: str, policy: str) -> dict[str, str]:
    return {"model": model, "preprocessing": prep, "data": data, "policy": policy}


INCIDENTS["image_model_x_transpose"] = (
    img("lr_aug_transpose", "identity", "snapshot-a", "abstain-0.30"),
    img("lr_plain", "transpose", "snapshot-b", "abstain-0.10"),
    ["model", "preprocessing"],
    IMG,
)
INCIDENTS["image_model_x_shift"] = (
    img("lr_aug_shift", "identity", "snapshot-a", "abstain-0.30"),
    img("mlp", "shift-1", "snapshot-b", "abstain-0.10"),
    ["model", "preprocessing"],
    IMG,
)
INCIDENTS["image_dead_pixels"] = (
    img("lr_plain", "identity", "snapshot-a", "abstain-0.30"),
    img("lr_plain_b", "identity", "snapshot-c", "abstain-0.10"),
    ["data"],
    IMG,
)
INCIDENTS["image_invert"] = (
    img("lr_plain", "identity", "snapshot-a", "abstain-0.30"),
    img("lr_plain_b", "invert", "snapshot-b", "abstain-0.10"),
    ["preprocessing"],
    IMG,
)
INCIDENTS["image_blur"] = (
    img("mlp", "identity", "snapshot-a", "abstain-0.30"),
    img("mlp", "blur", "snapshot-b", "abstain-0.10"),
    ["preprocessing"],
    IMG,
)


# ---- environment versions (pandas 2 vs pandas 3, real interpreters) -------------------------
ENV = replay(
    "real_env",
    "cases.json",
    120,
    interpreters={
        "component": "environment",
        "map": {
            "pandas2": "../../examples/real_env/envs/pandas2/bin/python",
            "pandas3": "../../examples/real_env/envs/pandas3/bin/python",
        },
    },
)


def env(model: str, prep: str, environment: str, policy: str) -> dict[str, str]:
    return {"model": model, "preprocessing": prep, "environment": environment, "policy": policy}


INCIDENTS["env_prep_x_pandas3"] = (
    env("m1", "impute-loc", "pandas2", "threshold-0.50"),
    env("m2", "impute-chained", "pandas3", "threshold-0.45"),
    ["preprocessing", "environment"],
    ENV,
)
INCIDENTS["env_pandas3_upgrade"] = (
    env("m1", "impute-chained", "pandas2", "threshold-0.50"),
    env("m2", "impute-chained", "pandas3", "threshold-0.45"),
    ["environment"],
    ENV,
)
CONTROLS["ctrl_env_model_needs_new_pandas"] = (
    env("m1", "impute-loc", "pandas2", "threshold-0.50"),
    env("m3", "impute-chained", "pandas3", "threshold-0.50"),
    "inferred",
    ENV,
)


# ---- noisy metrics: retrain per replay with a fresh seed (digits, MLP) ----------------------
NOISY = replay("real_noisy", "cases.json", 120, repeats=6, max_repeats=24, confidence=0.95)


def noisy(train_data: str, width: str, label_noise: str, dtype: str, epochs: str) -> dict[str, str]:
    return {
        "train_data": train_data,
        "width": width,
        "label_noise": label_noise,
        "eval_dtype": dtype,
        "epochs": epochs,
    }


INCIDENTS["noisy_data_x_width"] = (
    noisy("full", "64", "0.0", "float64", "40"),
    noisy("subset-600", "24", "0.3", "float32", "40"),
    ["train_data", "width"],
    NOISY,
)
INCIDENTS["noisy_labels_x_width_borderline"] = (
    noisy("full", "64", "0.0", "float64", "40"),
    noisy("subset-1100", "16", "0.6", "float32", "40"),
    ["label_noise", "width"],
    NOISY,
)
INCIDENTS["noisy_epochs"] = (
    noisy("full", "64", "0.0", "float64", "40"),
    noisy("subset-1100", "64", "0.3", "float32", "6"),
    ["epochs"],
    NOISY,
)


def main() -> None:
    from_static = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
    truth = {key: value for key, value in from_static.items() if key.startswith("churn_")}
    (ROOT / "incidents").mkdir(exist_ok=True)
    (ROOT / "controls").mkdir(exist_ok=True)
    for name, (good, bad, cause, spec) in INCIDENTS.items():
        manifest = {"id": name, "good": good, "bad": bad, "replay": spec}
        (ROOT / "incidents" / f"{name}.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        truth[name] = cause
    (ROOT / "ground_truth.json").write_text(
        json.dumps(truth, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    expected = {}
    for name, (good, bad, status, spec) in CONTROLS.items():
        manifest = {"id": name, "good": good, "bad": bad, "replay": spec}
        path = ROOT / "controls" / f"{name}.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        expected[name] = status
    (ROOT / "controls" / "expected_status.json").write_text(
        json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(INCIDENTS)} incidents and {len(CONTROLS)} controls")


if __name__ == "__main__":
    main()
