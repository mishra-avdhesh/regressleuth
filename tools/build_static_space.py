"""Build the API-free static Space from bundled, deterministic oracle incidents."""

from __future__ import annotations

import json
from pathlib import Path

from regressleuth import __version__
from regressleuth.bench import build_suite, run_one
from regressleuth.reporting import render_html

ROOT = Path(__file__).resolve().parents[1] / "space_static"
REPORTS = ROOT / "reports"
INCIDENTS = ("pair_model_preprocessing_k5", "control_double_healer_k6")
STRATEGIES = ("adaptive", "ddmin")
AUDITS = ("extended", "full")
BUDGET = 16


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    suite = {spec.id: spec for spec in build_suite()}
    snapshots: list[dict[str, object]] = []

    for incident_id in INCIDENTS:
        spec = suite[incident_id]
        for strategy in STRATEGIES:
            for audit in AUDITS:
                report = run_one(spec, strategy, BUDGET, seed=0, audit=audit)
                data = report.to_dict()
                filename = f"{incident_id}_{strategy}_{audit}.html"
                document = render_html(report).replace(
                    "<main>",
                    '<main><p class="mute">Precomputed snapshot of a bundled synthetic oracle '
                    "incident. This page does not run a new investigation. A 'verified' result is "
                    "verified under the configured replay model, assumptions, and audit checks.</p>",
                    1,
                )
                (REPORTS / filename).write_text(document, encoding="utf-8")
                snapshots.append(
                    {
                        "incident": incident_id,
                        "kind": spec.kind,
                        "ground_truth": sorted(spec.cause),
                        "strategy": strategy,
                        "audit": audit,
                        "budget": BUDGET,
                        "status": data["status"],
                        "diagnosis": data["diagnosis"],
                        "isolation_replays": data["replays"]["isolation_used"],
                        "audit_replays": data["replays"]["audit_used"],
                        "total_replays": data["replays"]["total"],
                        "interval": data["verification"]["interval_method"],
                        "interval_applied": data["verification"]["interval_applied"],
                        "report": f"reports/{filename}",
                    }
                )

    manifest = {"tool_version": __version__, "snapshots": snapshots}
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(snapshots)} static reports for Regressleuth {__version__}")


if __name__ == "__main__":
    main()
