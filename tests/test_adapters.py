"""Every adapter honors the same replay contract: metric, incompatible or classified error."""

from __future__ import annotations

import json
import os
import socket
import stat
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

from regressleuth import Incident
from regressleuth.adapters import (
    CommandAdapter,
    DockerAdapter,
    HTTPAdapter,
    PythonCallableAdapter,
    ReplayRequest,
    adapter_summary,
    build_adapter,
)
from regressleuth.adapters.base import portable
from regressleuth.errors import IncompatibleReplay, ReplayError

REQUEST = ReplayRequest({"model": "v2"}, seed=3, metric="accuracy", cases=None)


def script(tmp_path: Path, body: str) -> CommandAdapter:
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import json, sys, os, time\nstate = json.load(open(sys.argv[1])); out = sys.argv[2]\n" + body,
        encoding="utf-8",
    )
    return CommandAdapter(["{python}", str(runner), "{state}", "{result}"], cwd=tmp_path, timeout_seconds=5)


# --- command adapter -----------------------------------------------------------------------


def test_command_success_passes_state_and_captures_output(tmp_path: Path) -> None:
    adapter = script(
        tmp_path,
        "print('hello stdout'); print('oops', file=sys.stderr)\n"
        "json.dump({'metric': 0.5 + state['seed'] / 10}, open(out, 'w'))\n",
    )
    outcome = adapter.replay(REQUEST)
    assert outcome.status == "ok" and outcome.metric == pytest.approx(0.8)
    assert "hello stdout" in outcome.stdout_tail and "oops" in outcome.stderr_tail


@pytest.mark.parametrize(
    ("body", "status", "kind"),
    [
        ("sys.exit(3)\n", "error", "nonzero_exit"),
        ("time.sleep(10)\n", "error", "timeout"),
        ("pass\n", "error", "bad_output"),
        ("open(out, 'w').write('[1]')\n", "error", "bad_output"),
        ("json.dump({'metric': 1, 'extra': 2}, open(out, 'w'))\n", "error", "bad_output"),
        ("json.dump({'metric': 'high'}, open(out, 'w'))\n", "error", "invalid_metric"),
        ("json.dump({'status': 'incompatible'}, open(out, 'w'))\n", "incompatible", None),
    ],
)
def test_command_failures_are_classified(tmp_path: Path, body: str, status: str, kind: str | None) -> None:
    adapter = script(tmp_path, body)
    adapter.timeout_seconds = 1
    outcome = adapter.replay(REQUEST)
    assert (outcome.status, outcome.error_kind) == (status, kind)


def test_command_start_failure_and_callable_interface(tmp_path: Path) -> None:
    adapter = CommandAdapter(["/definitely/not/here"], cwd=tmp_path)
    assert adapter.replay(REQUEST).error_kind == "start_failed"
    with pytest.raises(ReplayError) as caught:
        adapter({"model": "v2"}, None, "accuracy")
    assert caught.value.kind == "start_failed"
    incompatible = script(tmp_path, "json.dump({'status': 'incompatible'}, open(out, 'w'))\n")
    with pytest.raises(IncompatibleReplay):
        incompatible({"model": "v2"}, None, "accuracy")
    assert len(incompatible.history) == 1
    with pytest.raises(ValueError):
        CommandAdapter([], cwd=tmp_path)


def test_command_environment_expansion_and_minimal_inheritance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RL_TOKEN", "s3cret-value")
    monkeypatch.setenv("RL_OTHER", "visible")
    body = "json.dump({'metric': float(os.environ.get('TOKEN') == 's3cret-value') + float('RL_OTHER' in os.environ)}, open(out, 'w'))\n"
    adapter = script(tmp_path, body)
    adapter.env = {"TOKEN": "${RL_TOKEN}"}
    assert adapter.replay(REQUEST).metric == 2.0
    adapter.inherit_env = False
    assert adapter.replay(REQUEST).metric == 1.0
    assert "s3cret-value" not in json.dumps(adapter.describe())
    adapter.env = {"TOKEN": "${RL_MISSING}"}
    assert adapter.replay(REQUEST).error_kind == "adapter_unavailable"


def test_command_placeholders_and_interpreter_selection(tmp_path: Path) -> None:
    runner = tmp_path / "echo.py"
    runner.write_text("import json, sys\njson.dump({'metric': float(sys.argv[2])}, open(sys.argv[1], 'w'))\n")
    adapter = CommandAdapter(
        ["{python}", str(runner), "{result}", "{seed}"],
        cwd=tmp_path,
        interpreter_component="env",
        interpreters={"a": "current", "b": "nope/python"},
    )
    assert adapter.replay(ReplayRequest({"env": "a"}, seed=7)).metric == 7.0
    assert adapter.replay(ReplayRequest({"env": "b"})).error_kind == "missing_interpreter"
    described = adapter.describe()
    assert described["interpreters"]["map"]["a"] == "current"
    assert all(not part.startswith("/") for part in described["command"])


def test_portable_paths() -> None:
    assert portable("/srv/project/run.py") == ".../run.py"
    assert portable("C:\\work\\run.py") == ".../run.py"
    assert portable("../runners/run.py") == "../runners/run.py"


# --- python adapter ------------------------------------------------------------------------


def test_python_adapter_passes_seed_and_cases_when_accepted(tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    def run(components: dict[str, Any], seed: int, cases: Path) -> float:
        seen.update(seed=seed, cases=cases, components=components)
        return 0.25

    adapter = PythonCallableAdapter(run)
    outcome = adapter.replay(ReplayRequest({"m": 1}, seed=5, cases=tmp_path))
    assert outcome.metric == 0.25 and seen == {"seed": 5, "cases": tmp_path, "components": {"m": 1}}
    assert PythonCallableAdapter(lambda c: 1.0).accepts_seed is False
    assert PythonCallableAdapter(lambda c, **kw: 1.0).accepts_seed is True


@pytest.mark.parametrize(
    ("raise_this", "status", "kind"),
    [
        (IncompatibleReplay("no"), "incompatible", None),
        (ReplayError("bad", kind="connection"), "error", "connection"),
        (RuntimeError("secret detail"), "error", "exception"),
    ],
)
def test_python_adapter_classifies_exceptions(raise_this: Exception, status: str, kind: str | None) -> None:
    def run(_components: dict[str, Any]) -> float:
        raise raise_this

    outcome = PythonCallableAdapter(run).replay(REQUEST)
    assert (outcome.status, outcome.error_kind) == (status, kind)
    assert "secret detail" not in outcome.message


def test_python_adapter_rejects_non_finite_and_times_out() -> None:
    assert PythonCallableAdapter(lambda c: float("nan")).replay(REQUEST).error_kind == "invalid_metric"
    slow = PythonCallableAdapter(lambda c: time.sleep(1) or 1.0, timeout_seconds=0.05)
    assert slow.replay(REQUEST).error_kind == "timeout"
    assert PythonCallableAdapter(lambda c: 2.0, timeout_seconds=1).replay(REQUEST).metric == 2.0


def test_python_adapter_from_reference(tmp_path: Path) -> None:
    (tmp_path / "pipeline_mod.py").write_text("def run(components):\n    return 0.9\n")
    adapter = PythonCallableAdapter.from_reference("pipeline_mod:run", search_path=tmp_path)
    assert adapter.replay(REQUEST).metric == 0.9 and adapter.describe()["callable"] == "pipeline_mod:run"
    for bad in ("pipeline_mod", "pipeline_mod:absent", "no_such_module_xyz:run"):
        with pytest.raises(ReplayError):
            PythonCallableAdapter.from_reference(bad, search_path=tmp_path)


# --- http adapter --------------------------------------------------------------------------


class Service(BaseHTTPRequestHandler):
    mode = "ok"
    seen_headers: ClassVar[dict[str, str]] = {}

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Service.seen_headers = dict(self.headers)
        if Service.mode == "slow":
            time.sleep(1)
        if Service.mode == "500":
            return self._send(500, {"error": "boom"})
        if Service.mode == "incompatible":
            return self._send(409, {"status": "incompatible"})
        if Service.mode == "garbage":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not json")
            return None
        components = body.get("components") or json.loads(self.headers.get("X-Regressleuth-Components", "{}"))
        if self.path == "/evaluate":
            return self._send(200, {"metric": 0.5 if components.get("model") == "v2" else 1.0})
        broken = components.get("model") == "v2"
        predictions = [(1 - x["y"]) if broken else x["y"] for x in body["instances"]]
        if Service.mode == "short":
            predictions = predictions[:-1]
        return self._send(200, {"predictions": predictions})

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_: Any) -> None:
        pass


@pytest.fixture
def service() -> Any:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    Service.mode = "ok"
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture
def cases(tmp_path: Path) -> Path:
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps({"input": {"y": i % 2}, "label": i % 2}) for i in range(10)))
    return path


def test_http_predict_scores_locally_with_header_or_body_routing(service: str, cases: Path) -> None:
    adapter = HTTPAdapter(
        service, cases=cases, batch_size=3, headers={"Authorization": "Bearer ${RL_HTTP_TOKEN}"}
    )
    os.environ["RL_HTTP_TOKEN"] = "tok-123"
    assert adapter.replay(ReplayRequest({"model": "v1"})).metric == 1.0
    assert Service.seen_headers["Authorization"] == "Bearer tok-123"
    assert adapter.replay(ReplayRequest({"model": "v2"})).metric == 0.0
    body = HTTPAdapter(service, cases=cases, components_via="body", metric="error_rate")
    assert body.replay(ReplayRequest({"model": "v2"})).metric == 1.0
    described = json.dumps(adapter.describe())
    assert "tok-123" not in described and "Authorization" in described


def test_http_evaluate_mode_and_numeric_metrics(service: str, cases: Path) -> None:
    adapter = HTTPAdapter(service, mode="evaluate")
    assert adapter.replay(ReplayRequest({"model": "v2"}, seed=2)).metric == 0.5
    for metric, expected in (("mae", 1.0), ("rmse", 1.0)):
        assert (
            HTTPAdapter(service, cases=cases, metric=metric).replay(ReplayRequest({"model": "v2"})).metric
            == expected
        )


@pytest.mark.parametrize(
    ("mode", "status", "kind"),
    [
        ("500", "error", "http_status"),
        ("incompatible", "incompatible", None),
        ("garbage", "error", "bad_output"),
        ("short", "error", "bad_output"),
        ("slow", "error", "timeout"),
    ],
)
def test_http_failures_are_classified(
    service: str, cases: Path, mode: str, status: str, kind: str | None
) -> None:
    Service.mode = mode
    outcome = HTTPAdapter(service, cases=cases, timeout_seconds=0.3).replay(ReplayRequest({"model": "v1"}))
    assert (outcome.status, outcome.error_kind) == (status, kind)


def test_http_connection_refused_and_bad_configuration(cases: Path) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    outcome = HTTPAdapter(f"http://127.0.0.1:{port}", cases=cases).replay(REQUEST)
    assert outcome.error_kind == "connection"
    assert HTTPAdapter("file:///etc", mode="evaluate").replay(REQUEST).error_kind == "adapter_unavailable"
    with pytest.raises(ValueError):
        HTTPAdapter("http://x", mode="stream")
    with pytest.raises(ValueError):
        HTTPAdapter("http://x", mode="predict")
    assert HTTPAdapter("${RL_URL}", mode="evaluate").describe()["base_url"] == "(from environment)"


# --- docker adapter (fake docker executable: no real daemon is used) -----------------------

FAKE_DOCKER = r"""
import json, os, subprocess, sys
args = sys.argv[1:]
log = os.environ["FAKE_DOCKER_LOG"]
with open(log, "a") as handle:
    handle.write(json.dumps(args) + "\n")
assert args[:4] == ["run", "--rm", "--network", "none"], args
mounts, i = {}, 4
while args[i] == "-v":
    host, container = args[i + 1].split(":")[:2]
    mounts[container] = host
    i += 2
image, inner = args[i], args[i + 1:]
def host_path(p):
    for container, host in mounts.items():
        if p.startswith(container):
            return host + p[len(container):]
    return p
inner = [host_path(p) for p in inner]
env = dict(os.environ, FAKE_IMAGE=image)
sys.exit(subprocess.run([sys.executable, *inner], env=env).returncode)
"""


def executable(directory: Path, name: str, source: str) -> Path:
    """A runnable fake tool; a /bin/sh wrapper keeps paths with spaces out of the shebang."""
    script = directory / f"{name}_impl.py"
    script.write_text(source, encoding="utf-8")
    wrapper = directory / name
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
    return wrapper


def test_docker_adapter_builds_isolated_command_and_selects_image(tmp_path: Path) -> None:
    docker = executable(tmp_path, "docker", FAKE_DOCKER)
    runner = tmp_path / "work_runner.py"
    runner.write_text(
        "import json, os, sys\nstate = json.load(open(sys.argv[1]))\n"
        "json.dump({'metric': 0.4 if os.environ['FAKE_IMAGE'] == 'img:new' else 0.9}, open(sys.argv[2], 'w'))\n"
    )
    cases = tmp_path / "cases.json"
    cases.write_text("[]")
    os.environ["FAKE_DOCKER_LOG"] = str(tmp_path / "log.jsonl")
    adapter = DockerAdapter(
        ["/regressleuth/work/../work_runner.py", "{state}", "{result}"],
        image_component="environment",
        images={"old": "img:old", "new": "img:new"},
        cases=cases,
        docker=str(docker),
    )
    # map the runner into the mounted work dir for the fake
    adapter.command = [str(runner), "{state}", "{result}"]
    assert adapter.replay(ReplayRequest({"environment": "old"})).metric == 0.9
    assert adapter.replay(ReplayRequest({"environment": "new"})).metric == 0.4
    calls = [json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert calls[0][calls[0].index("-v") + 1].endswith(":/regressleuth/work")
    assert any(arg.endswith(":/regressleuth/cases:ro") for arg in calls[0])
    assert adapter.describe()["experimental"] is True


def test_docker_adapter_errors(tmp_path: Path) -> None:
    missing = DockerAdapter(["x"], image="img", docker="no-such-docker-binary")
    assert missing.replay(REQUEST).error_kind == "adapter_unavailable"
    failing = executable(tmp_path, "docker", "import sys\nsys.exit(2)\n")
    assert DockerAdapter(["x"], image="img", docker=str(failing)).replay(REQUEST).error_kind == "nonzero_exit"
    empty = executable(tmp_path, "docker-empty", "import sys\nsys.exit(0)\n")
    assert DockerAdapter(["x"], image="img", docker=str(empty)).replay(REQUEST).error_kind == "bad_output"
    with pytest.raises(ValueError):
        DockerAdapter(["x"])


# --- factory -------------------------------------------------------------------------------


def spec(adapter: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "version": "1.0",
        "id": "a",
        "good": {"environment": "old"},
        "bad": {"environment": "new"},
        "metric": {"name": "accuracy", "direction": "higher_is_better", "regression_threshold": 0.1},
        "adapter": adapter,
        **extra,
    }


def test_build_adapter_for_every_type(tmp_path: Path) -> None:
    (tmp_path / "cases.jsonl").write_text('{"input": 1, "label": 1}\n')
    (tmp_path / "mod_x.py").write_text("def run(c):\n    return 1.0\n")
    kinds = {
        "command": {
            "type": "command",
            "command": ["{python}", "r.py"],
            "env": {"A": "b"},
            "interpreters": {"component": "environment", "map": {"old": "current", "new": "current"}},
        },
        "python": {"type": "python", "callable": "mod_x:run"},
        "http": {"type": "http", "base_url": "http://127.0.0.1:9", "headers": {"X-Key": "${K}"}},
        "docker": {
            "type": "docker",
            "command": ["python", "r.py"],
            "images": {"component": "environment", "map": {"old": "a:1", "new": "a:2"}},
        },
    }
    for kind, config in kinds.items():
        incident = Incident.from_spec(spec(config, cases="cases.jsonl"), base_dir=tmp_path)
        assert build_adapter(incident).kind == kind
        summary = adapter_summary(incident)
        assert summary["type"] == kind and "${K}" not in json.dumps(summary)
