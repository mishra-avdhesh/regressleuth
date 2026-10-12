"""Public errors from incident loading and replay."""

from __future__ import annotations


class RegressleuthError(Exception):
    """Base exception for the package."""


class InvalidIncident(RegressleuthError):
    """The incident specification cannot be investigated.

    ``problems`` lists every validation problem found, each prefixed with the location
    in the document (for example ``metric.direction``), so a user can fix them all at once.
    """

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = list(problems or [])


class ReplayError(RegressleuthError):
    """A replay did not produce a usable metric.

    ``kind`` classifies the failure for reports without exposing process output:
    timeout, start_failed, nonzero_exit, bad_output, invalid_metric, missing_interpreter,
    connection, http_status, adapter_unavailable or exception.
    """

    kind = "error"

    def __init__(self, message: str = "", *, kind: str | None = None) -> None:
        super().__init__(message)
        if kind is not None:
            self.kind = kind


class IncompatibleReplay(ReplayError):
    """A hybrid system cannot be assembled or evaluated."""

    kind = "incompatible"
