"""Run a trusted local command for each replay (no shell)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from ..errors import ReplayError
from ._env import SAFE_INHERITED, expand
from .base import Adapter, ReplayOutcome, ReplayRequest, finite_metric, portable, runtime_metadata, tail


class CommandAdapter(Adapter):
    """Write a state file, run an argument list, read a result file.

    Placeholders in ``command``: ``{python}`` (the interpreter, or the one selected by the
    ``interpreters`` component map), ``{state}``, ``{result}``, ``{cases}``, ``{seed}``.
    The state file holds ``components``, ``cases``, ``metric`` and ``seed``. The command
    writes ``{"metric": number}`` or ``{"status": "incompatible"}``. Exit status,
    timeout and malformed output are classified; stdout and stderr tails are kept in
    ``history`` for diagnostics and are never written to reports.
    """

    kind = "command"

    def __init__(
        self,
        command: list[str] | tuple[str, ...],
        *,
        cwd: Path,
        timeout_seconds: float = 600.0,
        cases: Path | None = None,
        env: dict[str, str] | None = None,
        inherit_env: bool = True,
        interpreter_component: str | None = None,
        interpreters: dict[str, str] | None = None,
        capture_bytes: int = 4096,
    ) -> None:
        super().__init__()
        if not command:
            raise ValueError("command must not be empty")
        self.command = tuple(command)
        self.cwd = Path(cwd)
        self.timeout_seconds = float(timeout_seconds)
        self.cases = cases
        self.env = dict(env or {})
        self.inherit_env = inherit_env
        self.interpreter_component = interpreter_component
        self.interpreters = dict(interpreters or {})
        self.capture_bytes = capture_bytes

    def _python(self, components: dict[str, Any]) -> str:
        if self.interpreter_component is None:
            return sys.executable
        choice = self.interpreters[components[self.interpreter_component]]
        if choice == "current":
            return sys.executable
        path = os.path.abspath(self.cwd / choice)  # no resolve(): keep virtualenv symlinks
        if not os.path.isfile(path):
            raise ReplayError("environment interpreter is missing", kind="missing_interpreter")
        return path

    def _environment(self) -> dict[str, str]:
        base = (
            dict(os.environ)
            if self.inherit_env
            else {k: os.environ[k] for k in SAFE_INHERITED if k in os.environ}
        )
        base.update({name: expand(value) for name, value in self.env.items()})
        return base

    def replay(self, request: ReplayRequest) -> ReplayOutcome:
        started = time.perf_counter()
        cases = request.cases if request.cases is not None else self.cases
        with tempfile.TemporaryDirectory(prefix="regressleuth-") as directory:
            work = Path(directory)
            state_path, result_path = work / "state.json", work / "result.json"
            out_path, err_path = work / "stdout", work / "stderr"
            state_path.write_text(
                json.dumps(
                    {
                        "components": request.components,
                        "cases": str(cases) if cases is not None else None,
                        "metric": request.metric,
                        "seed": request.seed,
                    },
                    allow_nan=False,
                ),
                encoding="utf-8",
            )

            def outcome(**kwargs: Any) -> ReplayOutcome:
                result = ReplayOutcome(duration_seconds=time.perf_counter() - started, **kwargs)
                for path, attr in ((out_path, "stdout_tail"), (err_path, "stderr_tail")):
                    if path.exists():
                        setattr(result, attr, tail(path.read_bytes(), self.capture_bytes))
                return result

            try:
                replacements = {
                    "{python}": self._python(request.components),
                    "{state}": str(state_path),
                    "{result}": str(result_path),
                    "{cases}": str(cases) if cases is not None else "",
                    "{seed}": str(request.seed),
                }
                argv = []
                for part in self.command:
                    for marker, value in replacements.items():
                        part = part.replace(marker, value)
                    argv.append(part)
                environment = self._environment()
            except ReplayError as exc:
                return outcome(status="error", error_kind=exc.kind, message=str(exc))
            try:
                with out_path.open("wb") as stdout, err_path.open("wb") as stderr:
                    completed = subprocess.run(
                        argv,
                        cwd=self.cwd,
                        env=environment,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=self.timeout_seconds,
                        check=False,
                    )
            except subprocess.TimeoutExpired:
                return outcome(
                    status="error",
                    error_kind="timeout",
                    message=f"replay exceeded {self.timeout_seconds:g} s",
                )
            except OSError:
                return outcome(
                    status="error", error_kind="start_failed", message="replay command could not be started"
                )
            if completed.returncode != 0:
                return outcome(
                    status="error",
                    error_kind="nonzero_exit",
                    message=f"replay exited with code {completed.returncode}",
                )
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return outcome(
                    status="error", error_kind="bad_output", message="replay did not write valid result JSON"
                )
            if not isinstance(result, dict):
                return outcome(
                    status="error", error_kind="bad_output", message="replay result must be an object"
                )
            if result.get("status") == "incompatible":
                return outcome(status="incompatible", message="hybrid artifacts are incompatible")
            if set(result) != {"metric"}:
                return outcome(
                    status="error",
                    error_kind="bad_output",
                    message="replay result must contain only a metric",
                )
            try:
                metric_value = finite_metric(result["metric"])
            except ReplayError as exc:
                return outcome(status="error", error_kind=exc.kind, message=str(exc))
            return outcome(status="ok", metric=metric_value)

    def describe(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.kind,
            "command": [portable(part) for part in self.command],
            "timeout_seconds": self.timeout_seconds,
            "inherit_env": self.inherit_env,
            "env_names": sorted(self.env),
            "runtime": runtime_metadata(),
        }
        if self.interpreter_component:
            data["interpreters"] = {
                "component": self.interpreter_component,
                "map": {k: portable(v) for k, v in sorted(self.interpreters.items())},
            }
        return data
