"""Exhaustively check the deterministic incident fixtures and their ground truth."""

from __future__ import annotations

import itertools
import json
import os
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _replay(incident: dict, incident_dir: Path, selected: frozenset[str], seed: int = 0) -> float | None:
    replay = incident["replay"]
    components = {
        key: incident["bad"][key] if key in selected else value for key, value in incident["good"].items()
    }
    cases = (incident_dir / replay["cases"]).resolve()
    interpreters = replay.get("interpreters")
    python = sys.executable
    if interpreters:
        python = os.path.abspath(incident_dir / interpreters["map"][components[interpreters["component"]]])
    with tempfile.TemporaryDirectory() as directory:
        state_path = Path(directory) / "state.json"
        result_path = Path(directory) / "result.json"
        state_path.write_text(
            json.dumps(
                {
                    "components": components,
                    "cases": str(cases),
                    "metric": replay["metric"],
                    "seed": seed,
                }
            ),
            encoding="utf-8",
        )
        replacements = {
            "{python}": python,
            "{state}": str(state_path),
            "{result}": str(result_path),
        }
        command = [replacements.get(part, part) for part in replay["command"]]
        subprocess.run(
            command,
            cwd=incident_dir,
            check=True,
            timeout=replay["timeout_seconds"],
            capture_output=True,
            text=True,
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("status") == "incompatible":
            return None
        return float(result["metric"])


def main(prefixes: tuple[str, ...] = ()) -> None:
    truth = json.loads((ROOT / "ground_truth.json").read_text(encoding="utf-8"))
    incidents = sorted((ROOT / "incidents").glob("*.json"))
    if {path.stem for path in incidents} != set(truth):
        raise AssertionError("ground truth and incident files must have matching IDs")
    if prefixes:
        incidents = [path for path in incidents if path.stem.startswith(prefixes)]

    for path in incidents:
        incident = json.loads(path.read_text(encoding="utf-8"))
        if incident["id"] != path.stem:
            raise AssertionError(f"incident ID does not match filename: {path}")
        changed = tuple(key for key in incident["good"] if incident["good"][key] != incident["bad"][key])
        cause = frozenset(truth[incident["id"]])
        if not cause or not cause.issubset(changed):
            raise AssertionError(f"invalid ground truth for {incident['id']}")

        seeds = range(20) if incident["replay"].get("repeats", 1) > 1 else range(1)
        masks = [
            frozenset(combination)
            for size in range(len(changed) + 1)
            for combination in itertools.combinations(changed, size)
        ]
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                mask: [pool.submit(_replay, incident, path.parent, mask, seed) for seed in seeds]
                for mask in masks
            }
            scores = {mask: [f.result() for f in futs] for mask, futs in futures.items()}
        for values in scores.values():
            if any(value is None for value in values):
                raise AssertionError(f"{incident['id']}: unexpected incompatible hybrid")
        means = {mask: statistics.fmean(values) for mask, values in scores.items()}
        baseline = means[frozenset()]
        threshold = incident["replay"]["regression_threshold"]
        failing = 0
        margin = float("inf")
        for selected, score in means.items():
            regressed = baseline - score > threshold - 1e-12
            margin = min(margin, abs(baseline - score - threshold))
            if regressed != cause.issubset(selected):
                raise AssertionError(
                    f"{incident['id']}: {sorted(selected)} yielded {score:.3f}; "
                    f"expected {'fail' if cause.issubset(selected) else 'pass'}"
                )
            failing += regressed
        noise_note = ""
        if len(seeds) > 1:
            worst_sd = max(statistics.stdev(values) for values in scores.values())
            noise_note = (
                f", mean over {len(seeds)} seeds, max sd {worst_sd:.3f}, "
                f"closest mean to threshold {margin:.3f}"
            )
        print(
            f"{incident['id']}: {2 ** len(changed)} combinations checked, "
            f"{failing} regressed, baseline accuracy {baseline:.3f}{noise_note}"
        )


if __name__ == "__main__":
    main(tuple(sys.argv[1:]))
