"""Replay every mask of the historical candidates and record the evidence before evaluation.

    python benchmarks/historical/reproduce.py INCIDENT_ID [...]

For each incident this writes, without running any search strategy:
  replay_table.json  observations for every component mask (the same table every strategy reads)
  provenance.json    sources, versions, exact environment freezes, commands and the test
  ground_truth.json  the independently supported cause, only when source and replay agree
and updates the candidate status: ``included`` when the replay confirms the reported good/bad
behaviour, ``disputed`` when it does not (kept, documented, excluded from accuracy).
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "benchmarks"))

from prove_ground_truth import table_for

from regressleuth import Incident

RETRIEVED = "2026-10-10"


def main(ids: list[str]) -> int:
    candidates_path = HERE / "CANDIDATES.jsonl"
    rows = [json.loads(line) for line in candidates_path.read_text().splitlines() if line.strip()]
    by_id = {row["incident_id"]: row for row in rows}
    lock = json.loads((HERE / "ENVIRONMENTS.lock.json").read_text())
    failures = 0
    for incident_id in ids:
        row = by_id[incident_id]
        folder = HERE / "incidents" / incident_id
        incident = Incident.from_file(folder / "incident.yaml")
        (component,) = incident.changed_components
        table = table_for(incident, workers=1)
        (folder / "replay_table.json").write_text(
            json.dumps({"incident": incident_id, "table": table}, indent=1, sort_keys=True) + "\n"
        )
        good_runs, bad_runs = table[""], table[component]
        good, bad = good_runs[0], bad_runs[0]
        attempt = {
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "good": good_runs,
            "bad": bad_runs,
        }
        with (folder / "reproduction_attempts.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(attempt, sort_keys=True) + "\n")
        if any(run["status"] != "ok" for run in (*good_runs, *bad_runs)):
            # A runner that cannot execute (missing interpreter, version mismatch, import error)
            # says nothing about the report: leave the candidate pending and fix the runtime.
            print(f"{incident_id}: REPLAY ERROR good={good_runs} bad={bad_runs}; status left unchanged")
            failures += 1
            continue
        envs = {
            version: path.split("/envs/")[1].split("/")[0] for version, path in incident.replay.interpreters
        }
        provenance = {
            "incident_id": incident_id,
            "source_urls": row["source_urls"],
            "source_date": row["source_date"],
            "source_type": row["source_type"],
            "source_retrieved_utc": RETRIEVED,
            "good": incident.good,
            "bad": incident.bad,
            "changed_components": list(incident.changed_components),
            "fixed_test_cases": row["fixed_test_cases"],
            "failure_metric": row["failure_metric"],
            "threshold": row["threshold"],
            "hybrid_replay_feasibility": "full; one changed component, both masks executed",
            "reproduction_command": f"python benchmarks/historical/reproduce.py {incident_id}",
            "reproduction_environment": {
                "host_platform": platform.platform(),
                "environments": {version: {"name": name, **lock[name]} for version, name in envs.items()},
            },
            "historical_claim": {
                "title": row["title"],
                "supported_root_cause": row["supported_root_cause"],
                "root_cause_evidence": row["root_cause_evidence"],
                "expected": "known-good version passes the fixed test; known-bad version fails it",
            },
            "observed": {"good": good_runs, "bad": bad_runs},
        }
        (folder / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
        confirmed = all(run["metric"] == 1.0 for run in good_runs) and all(
            run["metric"] == 0.0 for run in bad_runs
        )
        if confirmed:
            truth = {
                "incident_id": incident_id,
                "accepted_causes": [[component]],
                "established_before_evaluation": True,
                "evidence_urls": row["source_urls"],
                "support": (
                    f"{row['root_cause_evidence']} Controlled replay of both masks in matched "
                    f"environments: good={good['metric']}, bad={bad['metric']}."
                ),
                "discrepancy": None,
            }
            (folder / "ground_truth.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n")
            row["status"] = "included"
        else:
            row["status"] = "disputed"
            row["screening_notes"] = (
                row.get("screening_notes", "") + f" Replay did not confirm the report: "
                f"good={good}, bad={bad}. Kept as disputed; excluded from accuracy."
            )
        print(
            f"{incident_id}: good={good['status']}/{good['metric']} bad={bad['status']}/{bad['metric']} "
            f"-> {row['status']}"
        )
    candidates_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
