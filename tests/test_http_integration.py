"""End to end over HTTP: a local service with version routing, diagnosed through the CLI."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from regressleuth.cli import main

ROOT = Path(__file__).resolve().parents[1]
RELEASES = {
    "good": {"model": "v1", "features": "f1", "cache": "on"},
    "bad": {"model": "v2", "features": "f2", "cache": "off"},
}


class Gateway(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        versions = dict(RELEASES["bad"])
        versions.update(json.loads(self.headers.get("X-Regressleuth-Components", "{}")))
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        broken = versions["model"] == "v2" and versions["features"] == "f2"
        predictions = [
            1 - row["x"] if broken and i % 3 == 0 else row["x"] for i, row in enumerate(body["instances"])
        ]
        data = json.dumps({"predictions": predictions}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_: Any) -> None:
        pass


def test_cli_diagnoses_a_service_through_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("SERVICE_URL", f"http://127.0.0.1:{server.server_address[1]}")
    (tmp_path / "cases.jsonl").write_text(
        "\n".join(json.dumps({"input": {"x": i % 2}, "label": i % 2}) for i in range(30))
    )
    (tmp_path / "incident.yaml").write_text(
        "version: '1.0'\nid: svc\n"
        f"good: {json.dumps(RELEASES['good'])}\nbad: {json.dumps(RELEASES['bad'])}\n"
        "metric: {name: accuracy, direction: higher_is_better, regression_threshold: 0.1}\n"
        "budget: {max_replays: 8, audit: extended}\ncases: cases.jsonl\n"
        "adapter: {type: http, base_url: '${SERVICE_URL}', batch_size: 7}\n"
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["inspect", str(tmp_path / "incident.yaml")]) == 0
    assert '"base_url": "(from environment)"' in out.getvalue() and "No replay was run." in out.getvalue()
    result = tmp_path / "result.json"
    with contextlib.redirect_stdout(io.StringIO()):
        code = main(
            [
                "diagnose",
                str(tmp_path / "incident.yaml"),
                "--format",
                "json",
                "--output",
                str(result),
                "--diagnostics-dir",
                str(tmp_path / "diag"),
            ]
        )
    server.shutdown()
    data = json.loads(result.read_text())
    assert code == 0 and data["status"] == "verified" and data["diagnosis"] == ["features", "model"]
    assert data["adapter"]["type"] == "http" and "127.0.0.1" not in json.dumps(data["adapter"])
    assert len(list((tmp_path / "diag").glob("replay-*.json"))) == data["replays"]["total"]


@pytest.mark.skipif(
    importlib.util.find_spec("sklearn") is None or not (ROOT / "examples/http_service/artifacts").exists(),
    reason="needs scikit-learn and `python examples/http_service/prepare.py`",
)
def test_the_bundled_http_service_demo_runs_end_to_end() -> None:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    run = subprocess.run(
        [sys.executable, str(ROOT / "examples/http_service/run_demo.py")],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
    summary = json.loads((ROOT / "examples/http_service/out/summary.json").read_text())
    assert summary["status"] == "verified" and summary["root_cause"] == ["feature_assembler", "model"]
    assert summary["replays_executed"] < summary["full_exhaustive_replays"]
