"""A small production-style scoring service (standard library HTTP server + scikit-learn).

Each deployment is a *release*: a pinned version of every component. The known-good
release and the regressed release run as two processes on two ports. Like a canary or
feature-flag gateway, the service also accepts an `X-Regressleuth-Components` header
that pins individual component versions for one request; Regressleuth uses it to replay
hybrids. Unknown versions are rejected with HTTP 400.

    python service.py --release good --port 8701
    python service.py --release bad  --port 8702
"""

from __future__ import annotations

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import joblib
import numpy as np

HERE = Path(__file__).resolve().parent
RELEASES = {
    "good": {
        "model": "risk-model:v1",
        "feature_assembler": "fa-1.4",
        "threshold_config": "t-0.50",
        "cache": "lru-on",
        "log_format": "json",
    },
    "bad": {
        "model": "risk-model:v2",
        "feature_assembler": "fa-2.0",
        "threshold_config": "t-0.45",
        "cache": "lru-off",
        "log_format": "text",
    },
}
VERSIONS = {name: {RELEASES["good"][name], RELEASES["bad"][name]} for name in RELEASES["good"]}
MODELS: dict[str, tuple[Any, dict[str, Any]]] = {}


def model(version: str) -> tuple[Any, dict[str, Any]]:
    if version not in MODELS:
        stem = version.replace(":", "_")
        MODELS[version] = (
            joblib.load(HERE / "artifacts" / f"{stem}.joblib"),
            json.loads((HERE / "artifacts" / f"{stem}.json").read_text()),
        )
    return MODELS[version]


def predict(versions: dict[str, str], instances: list[dict[str, float]]) -> list[int]:
    estimator, meta = model(versions["model"])
    canonical = meta["feature_names"]
    # fa-1.4 assembles vectors in the training column order; fa-2.0 sorts feature names
    order = canonical if versions["feature_assembler"] == "fa-1.4" else sorted(canonical)
    matrix = np.array([[row[name] for name in order] for row in instances], dtype=float)
    if meta["input"] == "by_name":  # this model re-maps columns using the assembler's names
        matrix = matrix[:, [order.index(name) for name in canonical]]
    threshold = float(versions["threshold_config"].split("-")[1])
    return (estimator.predict_proba(matrix)[:, 1] >= threshold).astype(int).tolist()


class Handler(BaseHTTPRequestHandler):
    release = "good"

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send(200, {"status": "ok", "release": self.release, "versions": RELEASES[self.release]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/predict":
            self._send(404, {"error": "not found"})
            return
        versions = dict(RELEASES[self.release])
        pinned = self.headers.get("X-Regressleuth-Components")
        if pinned:
            try:
                requested = json.loads(pinned)
            except ValueError:
                self._send(400, {"error": "bad component header"})
                return
            for name, version in requested.items():
                if name not in VERSIONS or version not in VERSIONS[name]:
                    self._send(400, {"error": f"unknown version for {name}"})
                    return
                versions[name] = version
        try:
            length = int(self.headers.get("Content-Length", "0"))
            instances = json.loads(self.rfile.read(length))["instances"]
            self._send(200, {"predictions": predict(versions, instances)})
        except (KeyError, ValueError, TypeError):
            self._send(400, {"error": "bad request"})

    def log_message(self, *_args: Any) -> None:
        logging.debug("request")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", choices=sorted(RELEASES), required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    Handler.release = args.release
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"serving release {args.release} on http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
