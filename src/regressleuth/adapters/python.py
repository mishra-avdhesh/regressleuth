"""Call a trusted in-process Python function for each replay."""

from __future__ import annotations

import importlib
import inspect
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..errors import IncompatibleReplay, ReplayError
from .base import Adapter, ReplayOutcome, ReplayRequest, finite_metric, runtime_metadata


class PythonCallableAdapter(Adapter):
    """``fn(components)`` returns the metric. If ``fn`` accepts ``seed`` or ``cases``
    keyword arguments they are passed. Raise ``IncompatibleReplay`` for hybrids that cannot
    be built. ``timeout_seconds`` is best effort: the call runs in a worker thread and a
    late result is discarded, but Python cannot stop the thread itself.
    """

    kind = "python"

    def __init__(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__()
        self.fn = fn
        self.name = name or getattr(fn, "__qualname__", "callable")
        self.timeout_seconds = timeout_seconds
        parameters = inspect.signature(fn).parameters
        variadic = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())
        self.accepts_seed = variadic or "seed" in parameters
        self.accepts_cases = variadic or "cases" in parameters

    @classmethod
    def from_reference(
        cls, reference: str, *, search_path: Path | None = None, timeout_seconds: float | None = None
    ) -> PythonCallableAdapter:
        module_name, _, attribute = reference.partition(":")
        if not module_name or not attribute:
            raise ReplayError("callable must look like 'module:function'", kind="adapter_unavailable")
        if search_path is not None and str(search_path) not in sys.path:
            sys.path.insert(0, str(search_path))
        try:
            target: Any = importlib.import_module(module_name)
            for part in attribute.split("."):
                target = getattr(target, part)
        except (ImportError, AttributeError) as exc:
            raise ReplayError(f"cannot import {reference}", kind="adapter_unavailable") from exc
        return cls(target, name=reference, timeout_seconds=timeout_seconds)

    def _call(self, request: ReplayRequest) -> Any:
        kwargs: dict[str, Any] = {}
        if self.accepts_seed:
            kwargs["seed"] = request.seed
        if self.accepts_cases and request.cases is not None:
            kwargs["cases"] = request.cases
        return self.fn(dict(request.components), **kwargs)

    def replay(self, request: ReplayRequest) -> ReplayOutcome:
        started = time.perf_counter()
        box: dict[str, Any] = {}

        def target() -> None:
            try:
                box["value"] = self._call(request)
            except BaseException as exc:  # noqa: BLE001 - classified below
                box["error"] = exc

        if self.timeout_seconds is None:
            target()
        else:
            worker = threading.Thread(target=target, daemon=True)
            worker.start()
            worker.join(self.timeout_seconds)
            if worker.is_alive():
                return ReplayOutcome(
                    status="error",
                    error_kind="timeout",
                    message=f"callable exceeded {self.timeout_seconds:g} s",
                    duration_seconds=time.perf_counter() - started,
                )
        elapsed = time.perf_counter() - started
        error = box.get("error")
        if isinstance(error, IncompatibleReplay):
            return ReplayOutcome(status="incompatible", message=str(error), duration_seconds=elapsed)
        if isinstance(error, ReplayError):
            return ReplayOutcome(
                status="error", error_kind=error.kind, duration_seconds=elapsed, message=type(error).__name__
            )
        if error is not None:
            return ReplayOutcome(
                status="error", error_kind="exception", duration_seconds=elapsed, message=type(error).__name__
            )
        try:
            value = finite_metric(box.get("value"))
        except ReplayError as exc:
            return ReplayOutcome(
                status="error", error_kind=exc.kind, message=str(exc), duration_seconds=elapsed
            )
        return ReplayOutcome(status="ok", metric=value, duration_seconds=elapsed)

    def describe(self) -> dict[str, Any]:
        return {
            "type": self.kind,
            "callable": self.name,
            "timeout_seconds": self.timeout_seconds,
            "runtime": runtime_metadata(),
        }
