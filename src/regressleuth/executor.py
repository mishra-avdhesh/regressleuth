"""Backward-compatible name for the command adapter built from an incident."""

from __future__ import annotations

from .adapters import CommandAdapter, build_adapter
from .models import Incident


def CommandExecutor(incident: Incident) -> CommandAdapter:  # noqa: N802 - historical public name
    adapter = build_adapter(incident)
    if not isinstance(adapter, CommandAdapter):
        raise TypeError("incident does not use a command adapter")
    return adapter
