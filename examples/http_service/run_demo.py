"""End-to-end demo: start both releases, inspect, diagnose over HTTP, render the report.

python examples/http_service/prepare.py
python examples/http_service/run_demo.py
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait(url: str) -> dict:
    for _ in range(100):
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.loads(response.read())
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"service at {url} did not start")


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-m", "regressleuth.cli", *args]
    print("$ regressleuth " + " ".join(args), flush=True)
    return subprocess.run(command, cwd=HERE, text=True, capture_output=True, env=os.environ.copy())


def main() -> int:
    OUT.mkdir(exist_ok=True)
    ports = {"good": free_port(), "bad": free_port()}
    services = [
        subprocess.Popen(
            [sys.executable, str(HERE / "service.py"), "--release", r, "--port", str(p)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for r, p in ports.items()
    ]
    try:
        for release, port in ports.items():
            print(f"{release} release healthy: {wait(f'http://127.0.0.1:{port}/healthz')['versions']}")
        os.environ["REGRESSLEUTH_SERVICE_URL"] = f"http://127.0.0.1:{ports['bad']}"
        inspect = cli("inspect", "incident.yaml")
        print(inspect.stdout)
        started = time.perf_counter()
        diagnose = cli("diagnose", "incident.yaml", "--format", "json", "--output", "out/result.json")
        elapsed = time.perf_counter() - started
        report = cli("report", "out/result.json", "--format", "html", "--output", "out/report.html")
        text = cli("report", "out/result.json", "--format", "text")
        print(text.stdout)
        result = json.loads((OUT / "result.json").read_text())
        summary = {
            "changed_components": result["incident"]["changed_components"],
            "candidate_causes": result["search"]["hypothesis_count"],
            "full_exhaustive_replays": result["search"]["search_space"],
            "isolation_budget": result["replays"]["budget"],
            "replays_executed": result["replays"]["total"],
            "isolation_replays": result["replays"]["isolation_used"],
            "audit_replays": result["replays"]["audit_used"],
            "status": result["status"],
            "verification": result["verification"],
            "root_cause": result["diagnosis"],
            "wall_time_seconds": round(elapsed, 2),
            "exit_code": diagnose.returncode,
            "report": str((OUT / "report.html").relative_to(HERE)),
        }
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return 0 if report.returncode == 0 and diagnose.returncode == 0 else 1
    finally:
        for service in services:
            service.terminate()
            service.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
