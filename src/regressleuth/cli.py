"""Command line entry point.

Exit codes (stable): 0 verified; 2 a result that is not verified (inferred, inconclusive,
unresolved, invalid_baseline); 3 invalid input (incident, arguments or result file);
4 evaluation_error; 5 assumption_violated.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import Adapter, adapter_summary, build_adapter
from .engine import investigate
from .errors import InvalidIncident
from .git_manifest import compare_git_manifests
from .models import RESULT_SCHEMA_VERSION, Incident
from .redact import SECRET_VALUE
from .reporting import render_html, render_json, render_markdown, render_text
from .scaffold import FILES
from .spec import load_document, validate
from .strategies import STRATEGIES

DEMO_DIR = Path(__file__).resolve().parent / "_demo"
RENDERERS = {"text": render_text, "json": render_json, "markdown": render_markdown, "html": render_html}
EXIT = {"verified": 0, "evaluation_error": 4, "assumption_violated": 5}


def _emit(text: str, output: Path | None) -> None:
    if output:
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def exit_code(status: str) -> int:
    return EXIT.get(status, 2)


def _audit(value: str | None) -> int | str | None:
    if value is None or value in {"full", "extended"}:
        return value
    if not re.fullmatch(r"\d+", value):
        raise InvalidIncident("--audit must be full, extended or a non-negative integer")
    return int(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="regressleuth",
        description="Find which versioned change (or small set of changes) caused an ML regression.",
        epilog="Exit codes: 0 verified, 2 not verified, 3 invalid input, 4 evaluation error, "
        "5 assumption violated.",
    )
    parser.add_argument("--version", action="version", version=f"regressleuth {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    demo = sub.add_parser("demo", help="run the bundled offline example")
    demo.add_argument("--copy", type=Path, help="copy the demo files to this directory instead")
    demo.add_argument("--format", choices=tuple(RENDERERS), default="text")
    demo.add_argument("--output", type=Path)

    init = sub.add_parser("init", help="write a runnable incident.yaml + runner template")
    init.add_argument("directory", type=Path)
    init.add_argument("--force", action="store_true")

    check = sub.add_parser("validate", help="check an incident file against the specification")
    check.add_argument("incident", type=Path)

    inspect = sub.add_parser("inspect", help="show what a diagnosis would search (runs nothing)")
    inspect.add_argument("incident", type=Path)
    inspect.add_argument("--format", choices=("text", "json"), default="text")

    manifest_diff = sub.add_parser(
        "manifest-diff", help="compare JSON artifact manifests at two Git commits (runs nothing)"
    )
    manifest_diff.add_argument("repo", type=Path)
    manifest_diff.add_argument("good_ref")
    manifest_diff.add_argument("bad_ref")
    manifest_diff.add_argument("manifest_path")
    manifest_diff.add_argument("--include-values", action="store_true", help="show redacted version values")
    manifest_diff.add_argument("--output", type=Path)

    for name in ("diagnose", "investigate"):
        run = sub.add_parser(
            name, help="run a counterfactual diagnosis" if name == "diagnose" else "alias of diagnose"
        )
        run.add_argument("incident", type=Path)
        run.add_argument("--budget", type=int, help="isolation replays including both endpoints")
        run.add_argument("--strategy", choices=STRATEGIES)
        run.add_argument("--seed", type=int, help="seed for the random strategy")
        run.add_argument(
            "--audit", help="extended (default), full (historical), or max extra replays (0 skips)"
        )
        run.add_argument("--max-cause-size", type=int, choices=(1, 2, 3))
        run.add_argument("--format", choices=tuple(RENDERERS), default="text")
        run.add_argument("--output", type=Path)
        run.add_argument(
            "--diagnostics-dir",
            type=Path,
            help="write each replay's captured stdout/stderr tails here (local only)",
        )

    report = sub.add_parser("report", help="render a saved JSON result")
    report.add_argument("result", type=Path)
    report.add_argument("--format", choices=("text", "markdown", "html", "json"), default="text")
    report.add_argument("--output", type=Path)

    bench = sub.add_parser("bench", help="run the synthetic SleuthBench strategy comparison")
    bench.add_argument("--output-dir", type=Path, default=Path("benchmarks/results"))
    bench.add_argument("--seeds", type=int, default=10)

    schema = sub.add_parser("schema", help="print a JSON Schema (incident or result)")
    schema.add_argument("which", choices=("incident", "result"))
    return parser


def inspect_data(incident: Incident) -> dict[str, Any]:
    """Everything a diagnosis would do, computed without running any replay."""
    k = len(incident.changed_components)
    size = incident.search.max_cause_size
    pairs, triples = math.comb(k, 2), math.comb(k, 3)
    spec = incident.replay
    audit = incident.search.audit
    audit_cap = {"full": k, "extended": k + math.comb(max(k - 1, 0), 2)}.get(str(audit), audit)
    return {
        "id": incident.id,
        "spec_version": incident.spec_version,
        "description": incident.description,
        "changed_components": list(incident.changed_components),
        "unchanged_components": list(incident.unchanged_components),
        "search_space": 2**k,
        "candidate_causes": {
            "singletons": k,
            "pairs": pairs if size >= 2 else 0,
            "triples": triples if size >= 3 else 0,
            "triples_if_enabled": triples,
            "total_searched": k + (pairs if size >= 2 else 0) + (triples if size >= 3 else 0),
        },
        "full_exhaustive_replays": 2**k,
        "budget": {
            "isolation_max_replays": incident.search.budget or 8,
            "audit": audit,
            "audit_extra_replays_at_most": audit_cap,
        },
        "strategy": incident.search.strategy,
        "seed": incident.search.seed,
        "max_cause_size": size,
        "metric": {
            "name": spec.metric,
            "direction": "higher_is_better" if spec.direction == "higher" else "lower_is_better",
            "regression_threshold": spec.regression_threshold,
        },
        "noise": {
            "repeats": spec.repeats,
            "max_repeats": spec.max_repeats,
            "confidence": spec.confidence,
            "enabled": spec.max_repeats > 1,
        },
        "cases": spec.cases.name if spec.cases else None,
        "adapter": adapter_summary(incident),
        "assumptions": [
            "every replay scores the same labeled cases with the same metric",
            "a replay depends only on the declared component versions and the run seed",
            f"one minimal cause of at most {size} components",
            "failure persists as more bad components are added (tested by the audit)",
            "replays are deterministic or their noise is covered by the declared repeats",
        ],
    }


def _print_inspect(data: dict[str, Any]) -> None:
    causes = data["candidate_causes"]
    triples = (
        str(causes["triples"])
        if data["max_cause_size"] >= 3
        else f"not searched ({causes['triples_if_enabled']} with search.max_cause_size: 3)"
    )
    noise = data["noise"]
    noise_text = (
        f"repeats {noise['repeats']} up to {noise['max_repeats']}, confidence {noise['confidence']}"
        if noise["enabled"]
        else "off (one run per replay)"
    )
    budget = data["budget"]
    lines = [
        f"Incident          {data['id']}  (spec {data['spec_version']})",
        *([f"Description       {data['description'].strip()}"] if data["description"] else []),
        f"Changed ({len(data['changed_components'])})       {', '.join(data['changed_components'])}",
        f"Unchanged         {', '.join(data['unchanged_components']) or '-'}",
        f"Search space      {data['search_space']} combinations of good/bad versions",
        f"Candidate causes  {causes['total_searched']}: {causes['singletons']} single, "
        f"{causes['pairs']} pairs, triples {triples}",
        f"Full exhaustive   {data['full_exhaustive_replays']} replays",
        f"Budget            {budget['isolation_max_replays']} isolation replays (+ audit "
        f"{budget['audit']}, at most {budget['audit_extra_replays_at_most']} extra)",
        f"Strategy          {data['strategy']} (seed {data['seed']})",
        f"Metric            {data['metric']['name']}, "
        f"{data['metric']['direction'].replace('_', ' ')}, "
        f"regression threshold {data['metric']['regression_threshold']}",
        f"Noise             {noise_text}",
        f"Cases             {data['cases'] or '-'}",
        f"Adapter           {json.dumps(data['adapter'], sort_keys=True)}",
        "Assumptions       " + "\n                  ".join(data["assumptions"]),
        "No replay was run.",
    ]
    print("\n".join(lines))


def _write_diagnostics(adapter: Adapter, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for index, outcome in enumerate(adapter.history, 1):
        record = {
            "replay_call": index,
            "seed": outcome.seed,
            "status": outcome.status,
            "error_kind": outcome.error_kind,
            "message": outcome.message,
            "duration_seconds": round(outcome.duration_seconds, 4),
            "stdout_tail": SECRET_VALUE.sub("<redacted>", outcome.stdout_tail),
            "stderr_tail": SECRET_VALUE.sub("<redacted>", outcome.stderr_tail),
        }
        (directory / f"replay-{index:03d}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def _diagnose(args: argparse.Namespace) -> int:
    incident = Incident.from_file(args.incident)
    adapter = build_adapter(incident)
    try:
        result = investigate(
            incident,
            budget=args.budget,
            strategy=args.strategy,
            seed=args.seed,
            audit=_audit(args.audit),
            max_cause_size=args.max_cause_size,
            executor=adapter,
        )
    finally:
        adapter.close()
    if args.diagnostics_dir:
        _write_diagnostics(adapter, args.diagnostics_dir)
    _emit(RENDERERS[args.format](result), args.output)
    return exit_code(result.status)


def _validate(path: Path) -> int:
    document = load_document(path.resolve())
    if isinstance(document, dict) and "version" not in document:
        Incident.from_file(path)
        print(f"{path}: valid legacy (pre-1.0) manifest; consider migrating to specification 1.0")
        return 0
    problems = validate(document)
    if problems:
        print(f"{path}: {len(problems)} problem(s)", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 3
    Incident.from_file(path)
    print(f"{path}: valid (Incident Specification 1.0)")
    return 0


def _report(args: argparse.Namespace) -> int:
    try:
        data = json.loads(args.result.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != RESULT_SCHEMA_VERSION:
            raise ValueError(f"not a result schema {RESULT_SCHEMA_VERSION} file")
    except (OSError, ValueError) as exc:
        raise InvalidIncident(f"cannot read a valid result file: {exc}") from exc
    try:
        output = RENDERERS[args.format](data)
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidIncident("result file is incomplete or malformed") from exc
    _emit(output, args.output)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "bench":
            from . import bench as bench_module

            summary = bench_module.run_benchmark(seeds=args.seeds)
            bench_module.write_results(args.output_dir, summary)
            sys.stdout.write(bench_module.render_markdown(summary))
            return 0
        if args.command == "schema":
            name = f"{args.which}-1.0.schema.json"
            sys.stdout.write(
                resources.files("regressleuth").joinpath("schemas").joinpath(name).read_text("utf-8")
            )
            return 0
        if args.command == "init":
            if args.directory.exists() and any(args.directory.iterdir()) and not args.force:
                raise InvalidIncident(f"{args.directory} is not empty; use --force to overwrite")
            args.directory.mkdir(parents=True, exist_ok=True)
            for name, contents in FILES.items():
                (args.directory / name).write_text(contents, encoding="utf-8")
            print(
                f"Wrote a runnable template to {args.directory}/\n"
                f"Next:  regressleuth inspect {args.directory}/incident.yaml\n"
                f"       regressleuth diagnose {args.directory}/incident.yaml"
            )
            return 0
        if args.command == "demo":
            if args.copy:
                shutil.copytree(
                    DEMO_DIR, args.copy, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__")
                )
                print(
                    f"Copied the demo to {args.copy}/ - edit runner.py, then run:\n"
                    f"  regressleuth diagnose {args.copy}/incident.yaml"
                )
                return 0
            result = investigate(DEMO_DIR / "incident.yaml")
            _emit(RENDERERS[args.format](result), args.output)
            return exit_code(result.status)
        if args.command == "validate":
            return _validate(args.incident)
        if args.command == "inspect":
            data = inspect_data(Incident.from_file(args.incident))
            if args.format == "json":
                print(json.dumps(data, indent=2, sort_keys=True))
            else:
                _print_inspect(data)
            return 0
        if args.command == "manifest-diff":
            comparison = compare_git_manifests(
                args.repo,
                args.good_ref,
                args.bad_ref,
                args.manifest_path,
                include_values=args.include_values,
            )
            _emit(json.dumps(comparison, indent=2, sort_keys=True) + "\n", args.output)
            return 0
        if args.command in {"diagnose", "investigate"}:
            return _diagnose(args)
        return _report(args)
    except InvalidIncident as exc:
        print(f"regressleuth: {exc}", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
