"""Download the fixed SST-2 validation cases used by the text demo (needs network once)."""

from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

HERE = Path(__file__).resolve().parent


def main() -> None:
    data = load_dataset("stanfordnlp/sst2", split="validation")
    cases = [
        {"case_id": int(row["idx"]), "text": row["sentence"].strip(), "label": int(row["label"])}
        for row in data
    ]
    (HERE / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    print(f"wrote {len(cases)} fixed evaluation cases")


if __name__ == "__main__":
    main()
