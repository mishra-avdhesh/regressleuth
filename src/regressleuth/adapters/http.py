"""Replay against an HTTP service that can serve a requested mix of component versions."""

from __future__ import annotations

import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ..errors import ReplayError
from ._env import expand
from .base import Adapter, ReplayOutcome, ReplayRequest, finite_metric, runtime_metadata

METRICS = ("accuracy", "error_rate", "mae", "rmse")
DEFAULT_HEADER = "X-Regressleuth-Components"


def load_cases(path: Path) -> list[dict[str, Any]]:
    """JSON array or JSON Lines of objects."""
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    rows = (
        json.loads(text)
        if stripped.startswith("[")
        else [json.loads(line) for line in text.splitlines() if line.strip()]
    )
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError("cases must be a JSON array or JSON Lines of objects")
    return rows


def score(metric: str, predictions: list[Any], labels: list[Any]) -> float:
    if metric == "accuracy":
        return float(sum(p == y for p, y in zip(predictions, labels, strict=True))) / len(labels)
    if metric == "error_rate":
        return 1 - score("accuracy", predictions, labels)
    errors = [float(p) - float(y) for p, y in zip(predictions, labels, strict=True)]
    if metric == "mae":
        return sum(abs(e) for e in errors) / len(errors)
    if metric == "rmse":
        return math.sqrt(sum(e * e for e in errors) / len(errors))
    raise ValueError(f"unknown metric {metric}")


class HTTPAdapter(Adapter):
    """Two modes.

    ``predict``: the adapter sends the fixed cases' ``input`` fields in batches to
    ``POST {base_url}{path}`` as ``{"instances": [...]}`` and scores the returned
    ``{"predictions": [...]}`` against the cases' labels with a built-in metric
    (accuracy, error_rate, mae, rmse).
    ``evaluate``: the service computes the metric itself; the adapter posts
    ``{"components": ..., "seed": ..., "metric": ...}`` and reads ``{"metric": x}``.

    The requested versions travel in a JSON header (default ``X-Regressleuth-Components``)
    or in the request body, the way canary or feature-flag routing selects versions.
    A 409 or 422 response with ``{"status": "incompatible"}`` marks an unbuildable hybrid.
    Header values may reference environment variables as ``${NAME}``; values are never
    written to reports.
    """

    kind = "http"

    def __init__(
        self,
        base_url: str,
        *,
        mode: str = "predict",
        path: str | None = None,
        components_via: str = "header",
        header_name: str = DEFAULT_HEADER,
        timeout_seconds: float = 30.0,
        batch_size: int = 64,
        headers: dict[str, str] | None = None,
        cases: Path | None = None,
        metric: str = "accuracy",
        input_field: str = "input",
        label_field: str = "label",
        prediction_field: str = "predictions",
    ) -> None:
        super().__init__()
        if mode not in {"predict", "evaluate"}:
            raise ValueError("mode must be predict or evaluate")
        if components_via not in {"header", "body"}:
            raise ValueError("components_via must be header or body")
        if mode == "predict" and (cases is None or metric not in METRICS):
            raise ValueError(f"predict mode needs cases and a metric in {METRICS}")
        self.base_url = base_url
        self.mode = mode
        self.path = path or ("/predict" if mode == "predict" else "/evaluate")
        self.components_via = components_via
        self.header_name = header_name
        self.timeout_seconds = float(timeout_seconds)
        self.batch_size = int(batch_size)
        self.headers = dict(headers or {})
        self.cases_path = cases
        self.metric = metric
        self.input_field, self.label_field = input_field, label_field
        self.prediction_field = prediction_field
        self._cases: list[dict[str, Any]] | None = None

    def _url(self) -> str:
        url = expand(self.base_url).rstrip("/") + self.path
        if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
            raise ReplayError("base_url must use http or https", kind="adapter_unavailable")
        return url

    def _post(self, payload: dict[str, Any], components: dict[str, Any], seed: int) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Regressleuth-Seed": str(seed),
        }
        headers.update({name: expand(value) for name, value in self.headers.items()})
        if self.components_via == "header":
            headers[self.header_name] = json.dumps(components, sort_keys=True, separators=(",", ":"))
        else:
            payload = {**payload, "components": components}
        request = urllib.request.Request(  # noqa: S310 - _url() allows only http and https
            self._url(), data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:2048]
            if exc.code in {409, 422}:
                try:
                    if json.loads(detail).get("status") == "incompatible":
                        raise _Incompatible from None
                except (ValueError, AttributeError):
                    pass
            raise ReplayError(f"service answered HTTP {exc.code}", kind="http_status") from None
        except TimeoutError:
            raise ReplayError(f"no answer within {self.timeout_seconds:g} s", kind="timeout") from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise ReplayError("request timed out", kind="timeout") from None
            raise ReplayError("service unreachable", kind="connection") from None
        try:
            data = json.loads(body)
        except ValueError:
            raise ReplayError("service did not return JSON", kind="bad_output") from None
        if not isinstance(data, dict):
            raise ReplayError("service response must be a JSON object", kind="bad_output")
        if data.get("status") == "incompatible":
            raise _Incompatible
        return data

    def replay(self, request: ReplayRequest) -> ReplayOutcome:
        started = time.perf_counter()
        try:
            if self.mode == "evaluate":
                data = self._post(
                    {"seed": request.seed, "metric": request.metric}, request.components, request.seed
                )
                if set(data) != {"metric"}:
                    raise ReplayError("evaluate response must contain only a metric", kind="bad_output")
                value = finite_metric(data["metric"])
            else:
                if self._cases is None:
                    assert self.cases_path is not None
                    self._cases = load_cases(self.cases_path)
                predictions: list[Any] = []
                for start in range(0, len(self._cases), self.batch_size):
                    batch = self._cases[start : start + self.batch_size]
                    data = self._post(
                        {"instances": [c[self.input_field] for c in batch]}, request.components, request.seed
                    )
                    got = data.get(self.prediction_field)
                    if not isinstance(got, list) or len(got) != len(batch):
                        raise ReplayError("prediction count does not match the batch", kind="bad_output")
                    predictions.extend(got)
                labels = [c[self.label_field] for c in self._cases]
                try:
                    value = finite_metric(score(self.metric, predictions, labels))
                except (TypeError, ValueError):
                    raise ReplayError("predictions cannot be scored", kind="bad_output") from None
        except _Incompatible:
            return ReplayOutcome(
                status="incompatible",
                message="service reported an incompatible hybrid",
                duration_seconds=time.perf_counter() - started,
            )
        except ReplayError as exc:
            return ReplayOutcome(
                status="error",
                error_kind=exc.kind,
                message=str(exc),
                duration_seconds=time.perf_counter() - started,
            )
        except (OSError, KeyError, ValueError) as exc:
            return ReplayOutcome(
                status="error",
                error_kind="bad_output",
                message=type(exc).__name__,
                duration_seconds=time.perf_counter() - started,
            )
        return ReplayOutcome(status="ok", metric=value, duration_seconds=time.perf_counter() - started)

    def describe(self) -> dict[str, Any]:
        parts = urllib.parse.urlsplit(self.base_url)
        host = parts.hostname or parts.netloc
        shown = f"{parts.scheme}://{host}" + (f":{parts.port}" if parts.port else "")
        if "${" in self.base_url:
            shown = "(from environment)"
        return {
            "type": self.kind,
            "base_url": shown,
            "path": self.path,
            "mode": self.mode,
            "components_via": self.components_via,
            "batch_size": self.batch_size if self.mode == "predict" else None,
            "metric": self.metric if self.mode == "predict" else None,
            "header_names": sorted(self.headers),
            "timeout_seconds": self.timeout_seconds,
            "runtime": runtime_metadata(),
        }


class _Incompatible(Exception):
    pass
