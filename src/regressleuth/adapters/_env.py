"""Environment-variable expansion that keeps secret values out of reports."""

from __future__ import annotations

import os
import re

from ..errors import ReplayError

_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand(value: str) -> str:
    """Replace ${NAME} with the environment value; a missing variable is an error."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise ReplayError(f"environment variable {name} is not set", kind="adapter_unavailable")
        return os.environ[name]

    return _REFERENCE.sub(replace, value)


def references(value: str) -> list[str]:
    return _REFERENCE.findall(value)


SAFE_INHERITED = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT", "TZ")
