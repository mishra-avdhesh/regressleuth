"""EXPERIMENTAL: run each replay inside a container image chosen per component.

This adapter has been tested only against a fake ``docker`` executable that records and
emulates the command line (see tests). It has not been validated against a real Docker
daemon in this release; treat it as a starting point.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .base import Adapter, ReplayOutcome, ReplayRequest, finite_metric, portable, runtime_metadata, tail

CONTAINER_DIR = "/regressleuth"


class DockerAdapter(Adapter):
    """``docker run --rm --network none`` with the work directory mounted at /regressleuth.

    Placeholders in ``command`` resolve to container paths: ``{state}``, ``{result}``,
    ``{cases}`` (mounted read-only) and ``{seed}``. The image is fixed (``image``) or
    selected by a component (``image_component`` + ``images`` map), which is how an
    environment version becomes a real, isolated runtime.
    """

    kind = "docker"
    experimental = True

    def __init__(
        self,
        command: list[str],
        *,
        image: str | None = None,
        image_component: str | None = None,
        images: dict[str, str] | None = None,
        cases: Path | None = None,
        timeout_seconds: float = 600.0,
        network: str = "none",
        docker: str = "docker",
        capture_bytes: int = 4096,
    ) -> None:
        super().__init__()
        if (image is None) == (image_component is None):
            raise ValueError("give exactly one of image or image_component")
        self.command = list(command)
        self.image = image
        self.image_component = image_component
        self.images = dict(images or {})
        self.cases = cases
        self.timeout_seconds = float(timeout_seconds)
        self.network = network
        self.docker = docker
        self.capture_bytes = capture_bytes

    def _image(self, components: dict[str, Any]) -> str:
        if self.image is not None:
            return self.image
        assert self.image_component is not None
        return self.images[components[self.image_component]]

    def replay(self, request: ReplayRequest) -> ReplayOutcome:
        started = time.perf_counter()
        binary = shutil.which(self.docker)
        if binary is None:
            return ReplayOutcome(
                status="error", error_kind="adapter_unavailable", message="docker executable not found"
            )
        cases = request.cases if request.cases is not None else self.cases
        with tempfile.TemporaryDirectory(prefix="regressleuth-docker-") as directory:
            work = Path(directory)
            (work / "state.json").write_text(
                json.dumps(
                    {
                        "components": request.components,
                        "cases": f"{CONTAINER_DIR}/cases/{cases.name}" if cases else None,
                        "metric": request.metric,
                        "seed": request.seed,
                    }
                ),
                encoding="utf-8",
            )
            replacements = {
                "{state}": f"{CONTAINER_DIR}/work/state.json",
                "{result}": f"{CONTAINER_DIR}/work/result.json",
                "{cases}": f"{CONTAINER_DIR}/cases/{cases.name}" if cases else "",
                "{seed}": str(request.seed),
            }
            inner = []
            for part in self.command:
                for marker, value in replacements.items():
                    part = part.replace(marker, value)
                inner.append(part)
            argv = [binary, "run", "--rm", "--network", self.network, "-v", f"{work}:{CONTAINER_DIR}/work"]
            if cases is not None:
                argv += ["-v", f"{cases.parent}:{CONTAINER_DIR}/cases:ro"]
            argv += [self._image(request.components), *inner]
            try:
                completed = subprocess.run(
                    argv, capture_output=True, timeout=self.timeout_seconds, check=False
                )
            except subprocess.TimeoutExpired:
                return ReplayOutcome(
                    status="error",
                    error_kind="timeout",
                    message=f"container exceeded {self.timeout_seconds:g} s",
                    duration_seconds=time.perf_counter() - started,
                )
            except OSError:
                return ReplayOutcome(
                    status="error",
                    error_kind="start_failed",
                    message="docker could not be started",
                    duration_seconds=time.perf_counter() - started,
                )
            duration = time.perf_counter() - started
            out_tail = tail(completed.stdout, self.capture_bytes)
            err_tail = tail(completed.stderr, self.capture_bytes)

            def done(**fields: Any) -> ReplayOutcome:
                return ReplayOutcome(
                    duration_seconds=duration, stdout_tail=out_tail, stderr_tail=err_tail, **fields
                )

            if completed.returncode != 0:
                return done(
                    status="error",
                    error_kind="nonzero_exit",
                    message=f"container exited with code {completed.returncode}",
                )
            try:
                result = json.loads((work / "result.json").read_text(encoding="utf-8"))
                if result.get("status") == "incompatible":
                    return done(status="incompatible")
                if set(result) != {"metric"}:
                    raise ValueError
                metric_value = finite_metric(result["metric"])
            except Exception:  # noqa: BLE001 - any malformed result is bad output
                return done(
                    status="error", error_kind="bad_output", message="container did not write a valid result"
                )
            return done(status="ok", metric=metric_value)

    def describe(self) -> dict[str, Any]:
        return {
            "type": self.kind,
            "experimental": True,
            "command": [portable(part) for part in self.command],
            "image": self.image,
            "images": {"component": self.image_component, "map": self.images}
            if self.image_component
            else None,
            "network": self.network,
            "timeout_seconds": self.timeout_seconds,
            "runtime": runtime_metadata(),
        }
