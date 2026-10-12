"""Build the holdout data and models (run once; needs scikit-learn, pandas, pyarrow,
huggingface_hub and Pillow, plus network for the Adult and MNIST downloads).

Models are written as plain JSON weights so every interpreter in envs/ can load them.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CATEGORICAL = ["workclass", "education", "marital.status", "occupation", "relationship", "race", "sex"]
NUMERIC = ["age", "education.num", "capital.gain", "capital.loss", "hours.per.week"]


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def standardize(features: np.ndarray) -> tuple[np.ndarray, list[float], list[float]]:
    mean = features.mean(axis=0)
    scale = features.std(axis=0)
    scale[scale == 0] = 1.0
    return (features - mean) / scale, mean.tolist(), scale.tolist()


def binary_lr(features: np.ndarray, labels: np.ndarray, c_value: float, **extra: object) -> dict:
    z, mean, scale = standardize(features)
    model = LogisticRegression(C=c_value, max_iter=5000).fit(z, labels)
    return {"coef": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]),
            "classes": [str(c) for c in model.classes_], "mean": mean, "scale": scale, **extra}


def report(name: str, weights: dict, features: np.ndarray, labels: np.ndarray) -> None:
    z = (features - np.array(weights["mean"])) / np.array(weights["scale"])
    p = 1 / (1 + np.exp(-(z @ np.array(weights["coef"]) + weights["intercept"])))
    print(f"  {name}: eval accuracy {np.mean((p >= 0.5).astype(int) == labels):.3f}")


def flip(labels: np.ndarray, rng: np.random.RandomState, rate: float) -> np.ndarray:
    out = labels.copy()
    mask = rng.rand(len(out)) < rate
    out[mask] = 1 - out[mask]
    return out


def numpy_time() -> None:
    rng = np.random.RandomState(11)
    n = 7500
    reset = 1_700_000_000 + rng.randint(0, 30_000_000, n) + rng.rand(n)
    fraud = rng.rand(n) < 0.35
    delta = np.where(fraud, rng.uniform(0, 60, n), rng.uniform(60, 1800, n))
    labels = flip(fraud.astype(int), rng, 0.03)
    log_amount = rng.normal(4, 1, n) + 0.5 * fraud
    # a "within 60 s of the reset" rule feature, as fraud systems use (construction log entry 1)
    features = np.column_stack([(delta < 60).astype(float), delta / 60.0, log_amount])
    train, test = np.arange(6000), np.arange(6000, n)
    out = DATA / "numpy_time"
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        weights = binary_lr(features[train], labels[train], c_value)
        dump(out / f"{name}.json", weights)
        report(f"numpy_time {name}", weights, features[test], labels[test])
    dump(out / "cases.json", [{"case_id": int(i), "event_ts": float(reset[i] + delta[i]),
                               "reset_ts": float(reset[i]), "log_amount": float(log_amount[i]),
                               "label": int(labels[i])} for i in test])


def pandas_datetime() -> None:
    rng = np.random.RandomState(12)
    n = 7500
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    signup = [base + timedelta(seconds=int(s)) for s in rng.randint(0, 60_000_000, n)]
    fraud = rng.rand(n) < 0.30
    age_days = np.where(fraud, rng.uniform(0, 7, n), rng.uniform(7, 700, n))
    labels = flip(fraud.astype(int), rng, 0.03)
    log_amount = rng.normal(4, 1, n) + 0.4 * fraud
    features = np.column_stack([np.log1p(age_days), log_amount])
    train, test = np.arange(6000), np.arange(6000, n)
    out = DATA / "pandas_datetime"
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        weights = binary_lr(features[train], labels[train], c_value)
        dump(out / f"{name}.json", weights)
        report(f"pandas_datetime {name}", weights, features[test], labels[test])
    cases = []
    for i in test:
        signup_epoch = int(signup[i].timestamp())
        cases.append({"case_id": int(i), "signup": signup[i].strftime("%Y-%m-%d %H:%M:%S"),
                      "event_epoch": signup_epoch + int(age_days[i] * 86400),
                      "log_amount": float(log_amount[i]), "label": int(labels[i])})
    dump(out / "cases.json", cases)


def csv_country() -> None:
    rng = np.random.RandomState(13)
    n = 7500
    countries = ["US", "GB", "DE", "NA", "IN", "BR", "ZA", "KE"]
    probs = [0.2, 0.1, 0.1, 0.2, 0.15, 0.1, 0.075, 0.075]
    picked = rng.choice(countries, n, p=probs)
    fraud = np.where(picked == "NA", rng.rand(n) < 0.85, rng.rand(n) < 0.05)
    amount = np.round(np.exp(rng.normal(4, 1, n) + 0.3 * fraud), 2)
    onehot = np.array([[1.0 if c == k else 0.0 for k in countries] for c in picked])
    features = np.column_stack([onehot, np.log(amount)])
    labels = fraud.astype(int)
    train, test = np.arange(6000), np.arange(6000, n)
    out = DATA / "csv_country"
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        weights = binary_lr(features[train], labels[train], c_value, countries=countries)
        dump(out / f"{name}.json", weights)
        report(f"csv_country {name}", weights, features[test], labels[test])
    dump(out / "cases.json", [{"case_id": int(i), "country": str(picked[i]),
                               "amount": float(amount[i]), "label": int(labels[i])} for i in test])


def timezone_hours() -> None:
    rng = np.random.RandomState(14)
    n = 7500
    zone = ZoneInfo("America/New_York")
    start = datetime(2026, 1, 5, tzinfo=zone)
    local = [start + timedelta(seconds=int(s)) for s in rng.randint(0, 50 * 86400, n)]
    night = np.array([t.hour < 5 for t in local])
    fraud = np.where(night, rng.rand(n) < 0.70, rng.rand(n) < 0.05)
    log_amount = rng.normal(4, 1, n) + 0.3 * fraud
    hours = np.array([t.hour for t in local])
    features = np.column_stack([np.eye(24)[hours], log_amount])
    labels = fraud.astype(int)
    train, test = np.arange(6000), np.arange(6000, n)
    out = DATA / "timezone"
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        weights = binary_lr(features[train], labels[train], c_value)
        dump(out / f"{name}.json", weights)
        report(f"timezone {name}", weights, features[test], labels[test])
    dump(out / "cases.json", [{
        "case_id": int(i),
        "local_naive": local[i].strftime("%Y-%m-%d %H:%M:%S"),
        "utc_iso": local[i].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "log_amount": float(log_amount[i]), "label": int(labels[i])} for i in test])


def adult_frame() -> pd.DataFrame:
    path = hf_hub_download("scikit-learn/adult-census-income", "adult.csv", repo_type="dataset")
    frame = pd.read_csv(path)
    frame["label"] = (frame["income"].str.strip() == ">50K").astype(int)
    for column in CATEGORICAL:
        frame[column] = frame[column].astype(str).str.strip()
    frame["capital.gain"] = np.log1p(frame["capital.gain"])
    frame["capital.loss"] = np.log1p(frame["capital.loss"])
    return frame


def onehot(frame: pd.DataFrame, categories: dict[str, list[str]]) -> np.ndarray:
    blocks = [np.column_stack([(frame[c] == v).to_numpy(float) for v in categories[c]]) for c in CATEGORICAL]
    return np.column_stack([*blocks, frame[NUMERIC].to_numpy(float)])


def adult() -> None:
    frame = adult_frame()
    train, test = train_test_split(frame, test_size=0.3, random_state=0, stratify=frame["label"])
    categories = {c: sorted(train[c].unique().tolist()) for c in CATEGORICAL}
    out = DATA / "adult"
    case_fields = CATEGORICAL + NUMERIC + ["label"]

    def cases_of(part: pd.DataFrame) -> list[dict]:
        rows = part[case_fields].to_dict(orient="records")
        return [{"case_id": i, **{k: (float(v) if k in NUMERIC else v) for k, v in r.items()}}
                for i, r in enumerate(rows)]

    dump(out / "encoder_cases.json", cases_of(test))
    sample = test.sample(3000, random_state=1)
    dump(out / "sample_cases.json", cases_of(sample))
    x_train, x_test = onehot(train, categories), onehot(test, categories)
    base = {"categorical": CATEGORICAL, "categories": categories, "numeric": NUMERIC}
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        weights = binary_lr(x_train, train["label"].to_numpy(), c_value, **base)
        dump(out / f"encoder_{name}.json", weights)
        report(f"adult encoder {name}", weights, x_test, test["label"].to_numpy())
    for name, names in (("m_yesno", ("no", "yes")), ("m_relabeled", ("low_income", "high_income"))):
        text_labels = np.where(train["label"].to_numpy() == 1, names[1], names[0])
        z, mean, scale = standardize(x_train)
        model = LogisticRegression(C=1.0, max_iter=5000).fit(z, text_labels)
        dump(out / f"proba_{name}.json", {"coef": model.coef_[0].tolist(),
                                          "intercept": float(model.intercept_[0]),
                                          "classes": [str(c) for c in model.classes_],
                                          "mean": mean, "scale": scale, **base})
        print(f"  adult proba {name}: classes {list(model.classes_)}")
    tokens = sorted({f"{c}={v}" for c in CATEGORICAL for v in frame[c].unique()})
    mapping = json.loads(subprocess.run(
        [sys.executable, "-c",
         "import json,sys; t=json.load(sys.stdin); print(json.dumps({k: hash(k) % 512 for k in t}))"],
        input=json.dumps(tokens), capture_output=True, text=True, check=True,
        env={**os.environ, "PYTHONHASHSEED": "0"}).stdout)

    def hashed(part: pd.DataFrame) -> np.ndarray:
        rows = []
        for record in part[CATEGORICAL + NUMERIC].to_dict(orient="records"):
            vector = [0.0] * 512
            for column in CATEGORICAL:
                vector[mapping[f"{column}={record[column]}"]] += 1.0
            rows.append(vector + [float(record[n]) for n in NUMERIC])
        return np.array(rows)

    h_train, h_test = hashed(train), hashed(test)
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        weights = binary_lr(h_train, train["label"].to_numpy(), c_value,
                            categorical=CATEGORICAL, numeric=NUMERIC)
        dump(out / f"hashing_{name}.json", weights)
        report(f"adult hashing {name}", weights, h_test, test["label"].to_numpy())


def mnist() -> None:
    def load(split: str, count: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
        path = hf_hub_download("ylecun/mnist", f"mnist/{split}-00000-of-00001.parquet", repo_type="dataset")
        frame = pd.read_parquet(path).sample(count, random_state=seed)
        pixels = np.stack([np.array(Image.open(io.BytesIO(r["bytes"]))) for r in frame["image"]])
        return pixels, frame["label"].to_numpy()

    train_px, train_y = load("train", 12000, 0)
    test_px, test_y = load("test", 2000, 0)

    def nearest(pixels: np.ndarray) -> np.ndarray:
        return np.stack([np.asarray(Image.fromarray(p).resize((14, 14), Image.Resampling.NEAREST),
                                    dtype=float).ravel() / 255.0 for p in pixels])

    x_train, x_test = nearest(train_px), nearest(test_px)
    out = DATA / "mnist"
    for name, c_value in (("m1", 1.0), ("m1b", 0.3)):
        model = LogisticRegression(C=c_value, max_iter=300).fit(x_train, train_y)
        dump(out / f"{name}.json", {"coef": model.coef_.tolist(), "intercept": model.intercept_.tolist()})
        print(f"  mnist {name}: eval accuracy {model.score(x_test, test_y):.3f}")
    dump(out / "cases.json", [{"case_id": i, "pixels": p.ravel().tolist(), "label": int(y)}
                              for i, (p, y) in enumerate(zip(test_px, test_y, strict=True))])


STEPS = {f.__name__: f for f in (numpy_time, pandas_datetime, csv_country, timezone_hours, adult, mnist)}

if __name__ == "__main__":
    for name in sys.argv[1:] or list(STEPS):
        print(name)
        STEPS[name]()
