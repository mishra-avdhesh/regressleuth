"""Replay adapters: one contract, several ways to run a hybrid."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Adapter, ReplayOutcome, ReplayRequest, portable
from .command import CommandAdapter
from .docker import DockerAdapter
from .http import HTTPAdapter
from .python import PythonCallableAdapter

if TYPE_CHECKING:
    from ..models import Incident

__all__ = [
    "Adapter",
    "CommandAdapter",
    "DockerAdapter",
    "HTTPAdapter",
    "PythonCallableAdapter",
    "ReplayOutcome",
    "ReplayRequest",
    "adapter_summary",
    "build_adapter",
]


def build_adapter(incident: Incident) -> Adapter:
    """Create the adapter an incident declares (legacy manifests use the command adapter)."""
    spec = incident.replay
    config = incident.adapter
    if config is None:
        return CommandAdapter(
            spec.command,
            cwd=incident.base_dir,
            timeout_seconds=spec.timeout_seconds,
            cases=spec.cases,
            interpreter_component=spec.interpreter_component,
            interpreters=dict(spec.interpreters),
        )
    kind = config["type"]
    timeout = float(config.get("timeout_seconds", 600))
    if kind == "command":
        interp = config.get("interpreters")
        return CommandAdapter(
            config["command"],
            cwd=incident.base_dir / config.get("cwd", "."),
            timeout_seconds=timeout,
            cases=spec.cases,
            env=config.get("env"),
            inherit_env=config.get("inherit_env", True),
            interpreter_component=interp["component"] if interp else None,
            interpreters=interp["map"] if interp else None,
            capture_bytes=config.get("capture_bytes", 4096),
        )
    if kind == "python":
        return PythonCallableAdapter.from_reference(
            config["callable"],
            search_path=(incident.base_dir / config.get("path", ".")).resolve(),
            timeout_seconds=config.get("timeout_seconds"),
        )
    if kind == "http":
        return HTTPAdapter(
            config["base_url"],
            mode=config.get("mode", "predict"),
            path=config.get("path"),
            components_via=config.get("components_via", "header"),
            header_name=config.get("header_name", "X-Regressleuth-Components"),
            timeout_seconds=float(config.get("timeout_seconds", 30)),
            batch_size=config.get("batch_size", 64),
            headers=config.get("headers"),
            cases=spec.cases,
            metric=spec.metric,
            input_field=config.get("input_field", "input"),
            label_field=config.get("label_field", "label"),
            prediction_field=config.get("prediction_field", "predictions"),
        )
    images = config.get("images")
    return DockerAdapter(
        config["command"],
        image=config.get("image"),
        image_component=images["component"] if images else None,
        images=images["map"] if images else None,
        cases=spec.cases,
        timeout_seconds=timeout,
        network=config.get("network", "none"),
        docker=config.get("docker", "docker"),
    )


def adapter_summary(incident: Incident) -> dict[str, object]:
    """Describe the declared adapter from configuration only (imports and runs nothing)."""
    config = incident.adapter
    if config is None:
        return {
            "type": "command",
            "command": [portable(p) for p in incident.replay.command],
            "legacy_manifest": True,
        }
    summary: dict[str, object] = {"type": config["type"]}
    for key in (
        "command",
        "callable",
        "mode",
        "path",
        "components_via",
        "image",
        "network",
        "timeout_seconds",
        "batch_size",
        "inherit_env",
    ):
        if key in config:
            value = config[key]
            summary[key] = [portable(v) for v in value] if isinstance(value, list) else value
    if "base_url" in config:
        summary["base_url"] = "(from environment)" if "${" in config["base_url"] else config["base_url"]
    for key in ("env", "headers"):
        if key in config:
            summary[f"{key}_names"] = sorted(config[key])
    for key in ("interpreters", "images"):
        if key in config:
            summary[key] = {"component": config[key]["component"], "versions": sorted(config[key]["map"])}
    if config["type"] == "docker":
        summary["experimental"] = True
    return summary
