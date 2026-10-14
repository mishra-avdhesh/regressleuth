"""Lockfile-update incidents: screen, prepare, discover the fixed tests, replay.

    python benchmarks/lockdrift/study.py screen OWNER/REPO PR      # facts for screening, writes nothing
    python benchmarks/lockdrift/study.py prepare ID                # source at base, lockfiles, incident
    python benchmarks/lockdrift/study.py discover ID               # endpoint runs -> fixed tests
    python benchmarks/lockdrift/study.py replay ID                 # every mask -> ground truth, status

See SELECTION_PROTOCOL.md. Nothing here runs a Regressleuth search strategy. Clones,
sources and environments live in ``work/`` (git-ignored); the evidence for an incident is
written to ``incidents/<ID>/``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
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
from regressleuth.adapters import build_adapter
from regressleuth.adapters.base import ReplayRequest
from regressleuth.lockfile_runner import environment_for
from regressleuth.lockfiles import diff_pins, expand, read_lockfile, write_incident

BOTS = {"dependabot[bot]", "renovate[bot]", "dependabot-preview[bot]"}
POPULATION = {
    "numpy",
    "pandas",
    "scipy",
    "scikit-learn",
    "pyarrow",
    "polars",
    "torch",
    "tensorflow",
    "jax",
    "xgboost",
    "lightgbm",
    "statsmodels",
    "transformers",
}
LOCKFILE = re.compile(r"(^|/)(uv\.lock|poetry\.lock|[^/]*requirements[^/]*\.txt)$")
DEPENDENCY_FILE = re.compile(
    r"(^|/)(uv\.lock|poetry\.lock|[^/]*requirements[^/]*\.(txt|in)|pyproject\.toml)$"
)
TZDATA = "tzdata==2025.2"
MAX_FIXED_TESTS = 20


def git(repo: Path, *args: str, text: bool = True) -> Any:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text, check=False)
    if result.returncode:
        raise SystemExit(f"git {' '.join(args[:3])} failed: {result.stderr[-500:] if text else ''}")
    return result.stdout


def clone(owner_repo: str) -> Path:
    target = WORK / "repos" / owner_repo.replace("/", "__")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--bare",
                "--filter=blob:none",
                f"https://github.com/{owner_repo}",
                str(target),
            ],
            check=True,
        )
    return target


def pr_commits(repo: Path, number: int) -> tuple[str, str, int]:
    """(base, head, human commits on top): base = parent of the bot's first commit.

    Human commits on top of the bot's (merges of main, manual fixes) make the reported
    transition more than a dependency change; the diff from base to head then shows them.
    """
    git(repo, "fetch", "--quiet", "origin", f"+refs/pull/{number}/head:refs/pr/{number}")
    head = git(repo, "rev-parse", f"refs/pr/{number}").strip()
    rows = [
        row.split("\0")
        for row in git(repo, "log", "--first-parent", "--format=%H%x00%an", "-80", head).splitlines()
    ]
    index = 0
    while index < len(rows) and rows[index][1] not in BOTS:
        index += 1
    humans_on_top = index
    if index == len(rows):
        raise SystemExit("no bot commit on the first-parent chain")
    while index < len(rows) and rows[index][1] in BOTS:
        index += 1
    if index == len(rows):
        raise SystemExit("no non-bot ancestor in the first 80 commits")
    return rows[index][0], head, humans_on_top


def lock_pins(repo: Path, commit: str, path: str, python: str) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as scratch:
        target = Path(scratch) / Path(path).name
        target.write_bytes(git(repo, "show", f"{commit}:{path}", text=False))
        return read_lockfile(target, python)


def screen(owner_repo: str, number: int, python: str = "3.12") -> dict[str, Any]:
    repo = clone(owner_repo)
    base, head, humans_on_top = pr_commits(repo, number)
    changed_files = git(repo, "diff", "--name-only", base, head).split()
    locks = {}
    for path in changed_files:
        if LOCKFILE.search(path):
            try:
                good = lock_pins(repo, base, path, python)
                bad = lock_pins(repo, head, path, python)
            except (SystemExit, Exception) as exc:  # screening reports problems, never raises
                locks[path] = {"error": str(exc)[:300]}
                continue
            diff = diff_pins(good, bad)
            locks[path] = {
                "k": len(diff),
                "changed": {name: list(values) for name, values in diff.items()},
                "population": sorted(POPULATION & (set(good) | set(bad))),
            }
    workflows = {}
    for path in git(repo, "ls-tree", "-r", "--name-only", base, ".github/workflows").split():
        text = git(repo, "show", f"{base}:{path}")
        lines = [
            line.strip()
            for line in text.splitlines()
            if re.search(r"python-version|pytest|uv sync|uv run|pip install|poetry install|tox|nox", line)
        ]
        workflows[path] = lines[:25]

    def file_at(path: str) -> str | None:
        try:
            return str(git(repo, "show", f"{base}:{path}")).strip()[:400]
        except SystemExit:
            return None

    pyproject = file_at("pyproject.toml") or ""
    requires = re.search(r"requires-python\s*=\s*[\"']([^\"']+)", pyproject)
    return {
        "python_version_file": file_at(".python-version"),
        "requires_python": requires.group(1) if requires else None,
        "repo": owner_repo,
        "pr": number,
        "human_commits_on_top": humans_on_top,
        "base": base,
        "head": head,
        "changed_files": changed_files,
        "non_dependency_files": [f for f in changed_files if not DEPENDENCY_FILE.search(f)],
        "lockfiles": locks,
        "workflows": workflows,
    }


def load(incident_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [json.loads(line) for line in (HERE / "CANDIDATES.jsonl").read_text().splitlines() if line.strip()]
    for row in rows:
        if row["incident_id"] == incident_id:
            return rows, row
    raise SystemExit(f"{incident_id} is not in CANDIDATES.jsonl")


def save(rows: list[dict[str, Any]]) -> None:
    (HERE / "CANDIDATES.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def host_tzdb() -> Path:
    target = WORK / "tzdb"
    if not (target / "tzdata" / "zoneinfo").is_dir():
        subprocess.run(
            [str(UV), "pip", "install", "--quiet", "--no-deps", "--target", str(target), TZDATA], check=True
        )
    return target / "tzdata" / "zoneinfo"


def prepare(incident_id: str) -> None:
    _rows, row = load(incident_id)
    repo = clone(row["project"])
    base, head, _humans = pr_commits(repo, row["pr"])
    if (base, head) != (row["base_commit"], row["head_commit"]):
        raise SystemExit(f"recorded commits differ from the PR refs: {base} {head}")
    holder = WORK / "sources" / incident_id
    if holder.exists():
        shutil.rmtree(holder)
    source = holder / row.get("checkout_dir", "checkout")  # the directory name CI checks out into
    source.mkdir(parents=True)
    # one tarball request for the exact commit (no API quota); faster than a lazy partial-clone archive
    import urllib.request

    url = f"https://codeload.github.com/{row['project']}/tar.gz/{base}"
    with urllib.request.urlopen(url, timeout=600) as response, tempfile.TemporaryFile() as handle:
        shutil.copyfileobj(response, handle)
        handle.seek(0)
        with tarfile.open(fileobj=handle, mode="r:gz") as tar:
            members = tar.getmembers()
            top = members[0].name.split("/")[0]
            for member in members:
                if member.name == top:
                    continue
                member.name = member.name[len(top) + 1 :]
                tar.extract(member, source, filter="data")
    folder = HERE / "incidents" / incident_id
    folder.mkdir(parents=True, exist_ok=True)
    name = Path(row["lockfile"]).name
    (folder / "good").mkdir(exist_ok=True)
    (folder / "bad").mkdir(exist_ok=True)
    (folder / "good" / name).write_bytes(git(repo, "show", f"{base}:{row['lockfile']}", text=False))
    (folder / "bad" / name).write_bytes(git(repo, "show", f"{head}:{row['lockfile']}", text=False))
    built = write_incident(
        folder / "good" / name,
        folder / "bad" / name,
        project=source / row.get("project_subdir", "."),
        tests=row["ci_selection"],
        directory=folder,
        python=row["python"],
        incident_id=incident_id,
        install_project=row.get("install_project", "editable"),
        pytest_args=tuple(row.get("pytest_args", [])),
        test_environment={"PYTHONTZPATH": str(host_tzdb()), **row.get("test_environment", {})},
        force=True,
    )
    cases = json.loads((folder / "cases.json").read_text())
    cases["environments"] = "../../work/envs"
    cases["test_environment"]["PYTHONTZPATH"] = "../../work/tzdb/tzdata/zoneinfo"
    (folder / "cases.json").write_text(json.dumps(cases, indent=2, sort_keys=True) + "\n")
    print(f"{incident_id}: k={len(built['changed'])}: {', '.join(built['changed'])}")


OUTCOME_PLUGIN = """
import json, os
results, broken = {}, []

def pytest_collectreport(report):
    if report.failed:
        broken.append(report.nodeid)

def pytest_runtest_logreport(report):
    status = "failed" if report.failed else "skipped" if report.skipped else "passed"
    if results.get(report.nodeid) in (None, "passed"):
        results[report.nodeid] = status

def pytest_sessionfinish(session, exitstatus):
    with open(os.environ["LOCKDRIFT_OUTCOMES"], "w") as handle:
        json.dump({"results": results, "collection_errors": broken}, handle)
"""


def endpoint_report(folder: Path, side: str) -> dict[str, Any]:
    """Run the CI selection in one endpoint environment; record every node's outcome."""
    import os

    cases = json.loads((folder / "cases.json").read_text())
    incident = Incident.from_file(folder / "incident.yaml")
    state = incident.good if side == "good" else incident.bad
    pins = sorted([*cases["shared_pins"]] + [p for n, v in state.items() for p in expand(n, str(v))])
    cases["project"] = str((folder / cases["project"]).resolve())
    venv, compatible, detail = environment_for(
        cases, pins, (folder / cases["environments"]).resolve(), str(UV)
    )
    if not compatible:
        raise SystemExit(f"{side} endpoint cannot be installed (build_infeasible?): {detail[-800:]}")
    plugin_dir = WORK / "plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "lockdrift_outcomes.py").write_text(OUTCOME_PLUGIN)
    out = WORK / "reports" / f"{folder.name}-{side}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "TMPDIR"}}
    env.update({k: v for k, v in cases["test_environment"].items()})
    env["PYTHONTZPATH"] = str((folder / cases["test_environment"]["PYTHONTZPATH"]).resolve())
    env["PYTHONPATH"] = str(plugin_dir)
    env["LOCKDRIFT_OUTCOMES"] = str(out)
    completed = subprocess.run(
        [
            str(venv / "bin" / "python"),
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "lockdrift_outcomes",
            *cases["pytest_args"],
            *cases["tests"],
        ],
        cwd=cases["project"],
        env=env,
        capture_output=True,
        text=True,
        timeout=5400,
        check=False,
    )
    if not out.exists():
        raise SystemExit(
            f"{side}: pytest did not run (no_test_command?): {completed.stdout[-1500:]}{completed.stderr[-800:]}"
        )
    data: dict[str, Any] = json.loads(out.read_text())
    data["exit_code"] = completed.returncode
    return data


def discover(incident_id: str) -> None:
    rows, row = load(incident_id)
    folder = HERE / "incidents" / incident_id
    good = endpoint_report(folder, "good")
    bad = endpoint_report(folder, "bad")
    bad_results = dict(bad["results"])
    for module in bad["collection_errors"]:  # tests that cannot even be imported in the bad state
        for node in good["results"]:
            if node.startswith(f"{module}::") and node not in bad_results:
                bad_results[node] = "failed"
    differing = [
        node
        for node, status in bad_results.items()
        if status == "failed" and good["results"].get(node) == "passed"
    ]
    counts = {
        side: {s: sum(v == s for v in data["results"].values()) for s in ("passed", "failed", "skipped")}
        for side, data in (("good", good), ("bad", bad))
    }
    record = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": counts,
        "collection_errors": {"good": good["collection_errors"], "bad": bad["collection_errors"]},
        "exit_codes": {"good": good["exit_code"], "bad": bad["exit_code"]},
        "differing": differing,
        "fixed_tests": differing[:MAX_FIXED_TESTS],
    }
    (folder / "discovery.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"{incident_id}: good {counts['good']} bad {counts['bad']} differing {len(differing)}")
    if not differing:
        row["status"] = "disputed"
        row["replay_explanation"] = "No test passes in the good state and fails in the bad state."
    else:
        cases = json.loads((folder / "cases.json").read_text())
        cases["tests"] = record["fixed_tests"]
        (folder / "cases.json").write_text(json.dumps(cases, indent=2, sort_keys=True) + "\n")
        row["fixed_tests"] = record["fixed_tests"]
    save(rows)


def replay_masks(incident: Incident, masks: list[tuple[str, ...]]) -> dict[str, dict[str, Any]]:
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


def minimal_failing(
    components: tuple[str, ...], table: dict[str, list[dict[str, Any]]]
) -> tuple[list[list[str]], list[list[str]]]:
    """Strict and coupled minimal failing sets (version 1, addendum B3)."""
    import itertools

    def outcome(mask: tuple[str, ...]) -> str:
        run = table["|".join(sorted(mask))][0]
        return run["status"] if run["status"] != "ok" else ("fail" if run["metric"] < 0.5 else "pass")

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


def replay(incident_id: str, workers: int = 16) -> None:
    rows, row = load(incident_id)
    if row["status"] != "candidate" or not row.get("fixed_tests"):
        raise SystemExit(f"{incident_id}: needs status candidate and discovered fixed tests")
    folder = HERE / "incidents" / incident_id
    incident = Incident.from_file(folder / "incident.yaml")
    components = incident.changed_components
    endpoints = [(), tuple(components)]
    runs = [replay_masks(incident, endpoints) for _ in range(2)]
    with (folder / "replay_attempts.jsonl").open("a") as log:
        log.write(
            json.dumps(
                {"utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "endpoint_runs": runs},
                sort_keys=True,
            )
            + "\n"
        )
    full = "|".join(sorted(components))
    if any(run[key]["status"] == "error" for run in runs for key in run):
        print(f"{incident_id}: REPLAY ERROR at an endpoint {runs}; left pending")
        return
    reproduced = all(run[""]["metric"] == 1.0 and run[full]["metric"] == 0.0 for run in runs)
    if not reproduced:
        row["status"] = "disputed"
        row["replay_explanation"] = (
            f"Endpoint reruns with the fixed tests did not reproduce good pass / bad fail every time: {runs}"
        )
        save(rows)
        print(f"{incident_id}: disputed (endpoints not reproduced)")
        return
    table = table_for(incident, workers=workers)
    complete = len(table) == 2 ** len(components)
    (folder / "replay_table.json").write_text(
        json.dumps({"incident": incident_id, "complete": complete, "table": table}, indent=1, sort_keys=True)
        + "\n"
    )
    strict, coupled = minimal_failing(components, table)
    statuses: dict[str, int] = {}
    for values in table.values():
        statuses[values[0]["status"]] = statuses.get(values[0]["status"], 0) + 1
    provenance = {
        "incident_id": incident_id,
        "project": row["project"],
        "pr": row["pr"],
        "source_urls": row["source_urls"],
        "base_commit": row["base_commit"],
        "head_commit": row["head_commit"],
        "lockfile": row["lockfile"],
        "python": row["python"],
        "changed_components": list(components),
        "search_space": 2 ** len(components),
        "mask_statuses": statuses,
        "strict_minimal": strict,
        "coupled_minimal": coupled,
        "fixed_tests": row["fixed_tests"],
        "host_time_zone_database": TZDATA,
        "uv": subprocess.run([str(UV), "--version"], capture_output=True, text=True).stdout.strip(),
    }
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    if statuses.get("error") or not (strict or coupled):
        row["status"] = "disputed"
        row["replay_explanation"] = (
            f"Exhaustive table has {statuses.get('error', 0)} errors; strict {strict}, coupled {coupled}."
        )
    else:
        truth = {
            "incident_id": incident_id,
            "accepted_causes": strict + coupled,
            "strict_minimal": strict,
            "coupled_minimal": coupled,
            "established_before_evaluation": True,
            "evidence_urls": row["source_urls"],
        }
        (folder / "ground_truth.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n")
        row["status"] = "included"
    save(rows)
    print(
        f"{incident_id}: k={len(components)} {statuses} strict={strict} coupled={coupled} -> {row['status']}"
    )


def main(argv: list[str]) -> int:
    if len(argv) >= 4 and argv[1] == "screen":
        print(json.dumps(screen(argv[2], int(argv[3]), *(argv[4:5] or [])), indent=1))
        return 0
    if len(argv) == 3 and argv[1] in {"prepare", "discover", "replay"}:
        {"prepare": prepare, "discover": discover, "replay": replay}[argv[1]](argv[2])
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
