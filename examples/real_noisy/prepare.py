"""Write the fixed held-out evaluation cases for the noisy-training demo (offline)."""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

HERE = Path(__file__).resolve().parent


def main() -> None:
    data = load_digits()
    _, x_eval, _, y_eval = train_test_split(
        data.data / 16.0, data.target, test_size=0.3, random_state=0, stratify=data.target
    )
    cases = [
        {"case_id": i, "pixels": (row * 16).round(4).tolist(), "label": int(label)}
        for i, (row, label) in enumerate(zip(x_eval, y_eval, strict=True))
    ]
    (HERE / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    print(f"wrote {len(cases)} fixed evaluation cases")


if __name__ == "__main__":
    main()
