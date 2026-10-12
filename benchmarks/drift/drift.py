"""Build dependency-drift incidents from logged candidates (see SELECTION_PROTOCOL.md).

    python benchmarks/drift/drift.py fetch ID     # project tarball at the fixed commit, project wheel
    python benchmarks/drift/drift.py resolve ID   # good/bad resolutions, components, incident files
    python benchmarks/drift/drift.py replay ID    # every mask, endpoint rerun, ground truth, status

Nothing here runs a Regressleuth search strategy. Downloads, sources, wheels and virtual
environments live in ``work/`` (git-ignored); everything needed to audit an incident is
written to ``incidents/<ID>/``.
"""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORK = HERE / "work"
UV = PROJECT / ".venv" / "bin" / "uv"
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "benchmarks"))

from prove_ground_truth import table_for

from regressleuth import Incident


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def load_candidates() -> list[dict[str, Any]]:
    path = HERE / "CANDIDATES.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    )


def save_candidates(rows: list[dict[str, Any]]) -> None:
    (HERE / "CANDIDATES.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def record(incident_id: str) -> dict[str, Any]:
    for row in load_candidates():
        if row["incident_id"] == incident_id:
            return row
    raise SystemExit(f"{incident_id} is not in CANDIDATES.jsonl")


def uv_env() -> dict[str, str]:
    import os

    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(WORK)),
        "UV_CACHE_DIR": str(WORK / "uv-cache"),
        "UV_PYTHON_DOWNLOADS": "never",
        "UV_NO_PROGRESS": "1",
    }


def fetch(incident_id: str) -> dict[str, Any]:
    row = record(incident_id)
    url = f"https://codeload.github.com/{row['project']}/tar.gz/{row['fixed_commit']}"
    tarballs = WORK / "tarballs"
    tarballs.mkdir(parents=True, exist_ok=True)
    archive = tarballs / f"{incident_id}.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(url, timeout=300) as response:
            archive.write_bytes(response.read())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    source = WORK / "sources" / incident_id
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes()), mode="r:gz") as tar:
        top = tar.getmembers()[0].name.split("/")[0]
        for member in tar.getmembers():
            if member.name == top:
                continue
            member.name = member.name[len(top) + 1 :]
            tar.extract(member, source, filter="data")
    wheels = WORK / "wheels" / incident_id
    if wheels.exists():
        shutil.rmtree(wheels)
    env = {**uv_env(), **row.get("build_environment", {})}
    built = subprocess.run(
        [str(UV), "build", "--wheel", "--quiet", "--out-dir", str(wheels), str(source)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if built.returncode != 0:
        raise SystemExit(f"project wheel could not be built (build_infeasible?): {built.stderr[-1500:]}")
    (wheel,) = wheels.glob("*.whl")
    if not wheel.name.endswith("-none-any.whl"):
        raise SystemExit(f"project wheel is not pure Python (build_infeasible): {wheel.name}")
    info = {"url": url, "sha256": digest, "wheel": wheel.name}
    folder = HERE / "incidents" / incident_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "source.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    print(f"{incident_id}: source {digest[:12]}, wheel {wheel.name}")
    return info


def compile_at(incident_id: str, row: dict[str, Any], day: str) -> dict[str, str]:
    source = WORK / "sources" / incident_id
    (wheel,) = (WORK / "wheels" / incident_id).glob("*.whl")
    spec = row["requirements"]
    lines = []
    extras = ",".join(spec.get("project_extras", []))
    # the project's own wheel carries its metadata, so nothing is built during resolution
    lines.append(f"{row['distribution']}{f'[{extras}]' if extras else ''} @ {wheel.as_uri()}")
    lines += [f"-r {source / name}" for name in spec.get("requirement_files", [])]
    lines += spec.get("extra_requirements", [])
    folder = WORK / "resolve" / incident_id
    folder.mkdir(parents=True, exist_ok=True)
    request = folder / "requirements.in"
    request.write_text("\n".join(lines) + "\n")
    out = subprocess.run(
        [
            str(UV),
            "pip",
            "compile",
            str(request),
            "--quiet",
            "--no-header",
            "--no-annotate",
            "--python-version",
            row["python"],
            "--python-platform",
            "x86_64-manylinux_2_28",
            "--exclude-newer",
            f"{day}T23:59:59Z",
            "--only-binary",
            ":all:",
            "--no-emit-package",
            row["distribution"],
        ],
        capture_output=True,
        text=True,
        env=uv_env(),
        check=False,
    )
    if out.returncode != 0:
        raise SystemExit(f"resolution at {day} failed (unresolvable_requirements?): {out.stderr[-1500:]}")
    pins = {}
    for line in out.stdout.splitlines():
        line = line.split("#")[0].strip()
        if "==" in line:
            name, version = line.split("==", 1)
            pins[normalize(name)] = version.split(";")[0].strip()
    return pins


def resolve(incident_id: str) -> dict[str, Any]:
    row = record(incident_id)
    good = compile_at(incident_id, row, row["d_good"])
    bad = compile_at(incident_id, row, row["d_bad"])
    changed = sorted(name for name in set(good) | set(bad) if good.get(name) != bad.get(name))
    shared = sorted(f"{name}=={good[name]}" for name in good if name not in changed)
    folder = HERE / "incidents" / incident_id
    folder.mkdir(parents=True, exist_ok=True)
    for name, pins in (("good", good), ("bad", bad)):
        (folder / f"{name}.txt").write_text("".join(f"{k}=={v}\n" for k, v in sorted(pins.items())))
    info = json.loads((folder / "source.json").read_text())
    cases = {
        "incident": incident_id,
        "python": row["python"],
        "tests": row["test_node_ids"],
        "test_root": row.get("test_root", "."),
        "test_environment": row.get("test_environment", {}),
        "pytest_args": row.get("pytest_args", []),
        "test_timeout_seconds": row.get("test_timeout_seconds", 600),
        "project_wheel": info["wheel"],
        "shared_pins": shared,
    }
    (folder / "cases.json").write_text(json.dumps(cases, indent=2, sort_keys=True) + "\n")
    lines = [
        "version: '1.0'",
        f"id: {incident_id}",
        f"description: {json.dumps(row['title'])}",
        "good:",
        *[f"  {name}: {json.dumps(good.get(name, 'absent'))}" for name in changed],
        "bad:",
        *[f"  {name}: {json.dumps(bad.get(name, 'absent'))}" for name in changed],
        "metric: {name: drift_tests_pass, direction: higher_is_better, regression_threshold: 0.5}",
        "replay: {repeats: 1, max_repeats: 1, interval: student_t}",
        "search: {strategy: adaptive, max_cause_size: 2, seed: 0}",
        "budget: {max_replays: 32, audit: extended}",
        "cases: cases.json",
        "adapter:",
        "  type: command",
        "  command: ['{python}', ../../runner.py, --state, '{state}', --result, '{result}']",
        "  timeout_seconds: 1800",
        "",
    ]
    (folder / "incident.yaml").write_text("\n".join(lines))
    print(f"{incident_id}: {len(changed)} changed components: {', '.join(changed)}")
    return {"changed": changed, "good": good, "bad": bad}


def minimal_failing(
    components: tuple[str, ...], table: dict[str, list[dict[str, Any]]]
) -> tuple[list[list[str]], list[list[str]]]:
    """Strict minimal failing sets, and coupled-minimal sets (addendum B3)."""

    def outcome(mask: tuple[str, ...]) -> str:
        run = table["|".join(sorted(mask))][0]
        if run["status"] != "ok":
            return run["status"]
        return "fail" if run["metric"] < 0.5 else "pass"

    strict, coupled = [], []
    for size in range(1, len(components) + 1):
        for mask in itertools.combinations(components, size):
            if outcome(mask) != "fail":
                continue
            proper = [outcome(sub) for r in range(1, size) for sub in itertools.combinations(mask, r)]
            if all(result == "pass" for result in proper):
                strict.append(sorted(mask))
            elif "fail" not in proper and "error" not in proper and "incompatible" in proper:
                coupled.append(sorted(mask))
    return strict, coupled


def verify_sources(incident_id: str) -> None:
    """The extracted project tree must equal the downloaded tarball, file for file."""
    archive = WORK / "tarballs" / f"{incident_id}.tar.gz"
    source = WORK / "sources" / incident_id
    with tarfile.open(archive, mode="r:gz") as tar:
        top = tar.getmembers()[0].name.split("/")[0]
        for member in tar.getmembers():
            if not member.isfile():
                continue
            path = source / member.name[len(top) + 1 :]
            extracted = tar.extractfile(member)
            assert extracted is not None
            if not path.is_file() or path.read_bytes() != extracted.read():
                raise SystemExit(f"{incident_id}: project source differs from its tarball: {path}")


TZDATA = "tzdata==2025.2"


def prepare_host_tzdb() -> str:
    """A fixed, complete IANA time-zone database shared by every replay (see runner.py)."""
    target = WORK / "tzdb"
    if not (target / "tzdata" / "zoneinfo").is_dir():
        subprocess.run(
            [str(UV), "pip", "install", "--quiet", "--no-deps", "--target", str(target), TZDATA],
            check=True,
            env=uv_env(),
        )
    return TZDATA


def replay(incident_id: str, workers: int = 24) -> str:
    verify_sources(incident_id)
    tzdb = prepare_host_tzdb()
    rows = load_candidates()
    row = next(r for r in rows if r["incident_id"] == incident_id)
    folder = HERE / "incidents" / incident_id
    incident = Incident.from_file(folder / "incident.yaml")
    components = incident.changed_components
    started = datetime.now(timezone.utc)
    endpoints = [(), tuple(components)]
    first = table_for_masks(incident, endpoints)
    rerun = table_for_masks(incident, endpoints)
    full_key = "|".join(sorted(components))
    good, bad = first[""], first[full_key]
    deterministic = all(
        rerun[key]["status"] == first[key]["status"] and rerun[key].get("metric") == first[key].get("metric")
        for key in rerun
    )
    endpoints_ok = (
        good["status"] == "ok" and good["metric"] == 1.0 and bad["status"] == "ok" and bad["metric"] == 0.0
    )
    attempt = {"utc": started.isoformat(timespec="seconds"), "first": first, "rerun": rerun}
    with (folder / "replay_attempts.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(attempt, sort_keys=True) + "\n")
    if any(value["status"] == "error" for value in (*first.values(), *rerun.values())):
        # a runner that cannot execute says nothing about the report: stay pending, fix, retry
        print(f"{incident_id}: REPLAY ERROR at an endpoint {first}; status left as {row['status']}")
        return str(row["status"])
    if endpoints_ok and deterministic:
        table = table_for(incident, workers=workers)
        good, bad = table[""][0], table[full_key][0]
    else:  # disputed by its endpoints alone; the exhaustive table would not change that
        table = {key: [value] for key, value in first.items()}
    complete = len(table) == 2 ** len(components)
    (folder / "replay_table.json").write_text(
        json.dumps({"incident": incident_id, "complete": complete, "table": table}, indent=1, sort_keys=True)
        + "\n"
    )
    strict, coupled = minimal_failing(components, table) if complete else ([], [])
    accepted = strict + coupled
    blamed = {normalize(name) for name in row["blamed"]}
    supported = [cause for cause in accepted if blamed & set(cause)]
    statuses: dict[str, int] = {}
    for runs in table.values():
        statuses[runs[0]["status"]] = statuses.get(runs[0]["status"], 0) + 1
    problems = []
    if not (good["status"] == "ok" and good["metric"] == 1.0):
        problems.append(f"good state did not pass: {good}")
    if not (bad["status"] == "ok" and bad["metric"] == 0.0):
        problems.append(f"bad state did not fail: {bad}")
    if not deterministic:
        problems.append(f"endpoint rerun differs: {rerun}")
    if not supported and not problems:
        problems.append(f"no minimal failing set includes a blamed distribution {sorted(blamed)}: {accepted}")
    errors = statuses.get("error", 0)
    if errors and not problems:
        problems.append(f"{errors} mask replays errored")
    provenance = {
        "incident_id": incident_id,
        "source_urls": row["source_urls"],
        "source_date": row["source_date"],
        "project": row["project"],
        "fixed_commit": row["fixed_commit"],
        "d_good": row["d_good"],
        "d_bad": row["d_bad"],
        "python": row["python"],
        "requirements": row["requirements"],
        "source": json.loads((folder / "source.json").read_text()),
        "changed_components": list(components),
        "search_space": 2 ** len(components),
        "mask_statuses": statuses,
        "endpoint_rerun_identical": deterministic,
        "blamed_in_report": sorted(blamed),
        "minimal_failing_sets": strict,
        "coupled_minimal_sets": coupled,
        "replayed_utc": started.isoformat(timespec="seconds"),
        "host_time_zone_database": tzdb,
        "host": {
            "platform": sys.platform,
            "uv": subprocess.run([str(UV), "--version"], capture_output=True, text=True).stdout.strip(),
        },
    }
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    if problems:
        row["status"] = "disputed"
        row["screening_notes"] = (row.get("screening_notes", "") + " Replay: " + "; ".join(problems)).strip()
        (folder / "ground_truth.json").unlink(missing_ok=True)
    else:
        truth = {
            "incident_id": incident_id,
            "accepted_causes": accepted,
            "strict_minimal": strict,
            "coupled_minimal": coupled,
            "established_before_evaluation": True,
            "evidence_urls": row["source_urls"],
            "support": "strict and coupled minimal failing sets of the exhaustive replay table "
            "(addendum B3); the report blames "
            f"{sorted(blamed)}",
            "blamed_matches": supported,
        }
        (folder / "ground_truth.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n")
        row["status"] = "included"
    save_candidates(rows)
    print(f"{incident_id}: k={len(components)} statuses={statuses} minimal={accepted} -> {row['status']}")
    for problem in problems:
        print("  ", problem)
    return str(row["status"])


def table_for_masks(incident: Incident, masks: list[tuple[str, ...]]) -> dict[str, dict[str, Any]]:
    from regressleuth.adapters import build_adapter
    from regressleuth.adapters.base import ReplayRequest

    adapter = build_adapter(incident)
    out = {}
    for mask in masks:
        result = adapter.replay(
            ReplayRequest(
                incident.selected_state(frozenset(mask)), 0, incident.replay.metric, incident.replay.cases
            )
        )
        out["|".join(sorted(mask))] = {
            "status": result.status,
            "metric": result.metric,
            "error_kind": result.error_kind,
            "seconds": result.duration_seconds,
        }
    adapter.close()
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in {"fetch", "resolve", "replay"}:
        print(__doc__, file=sys.stderr)
        return 2
    for incident_id in argv[2:]:
        {"fetch": fetch, "resolve": resolve, "replay": replay}[argv[1]](incident_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
