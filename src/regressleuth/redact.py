"""Show component versions in reports without leaking secrets.

Policies: ``omit`` (default for specification 1.0) drops values; ``hashed`` shows only
fingerprints; ``redacted`` shows short values and masks common secret patterns.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SECRET_KEY = re.compile(
    r"(pass(word)?|secret|token|api[_-]?key|credential|auth|private[_-]?key|session)", re.IGNORECASE
)
SECRET_VALUE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|xox[abpr]-[A-Za-z0-9-]{8,}"
    r"|Bearer\s+\S+|-----BEGIN [A-Z ]*PRIVATE KEY|://[^/\s:@]+:[^/\s@]+@|eyJ[A-Za-z0-9_-]{10,}\.)"
)
MAX_SHOWN = 120


def fingerprint(value: Any) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
    return f"<sha256:{digest[:12]}>"


def _redact(value: Any, key: str | None) -> Any:
    if key is not None and SECRET_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, None) for v in value]
    if isinstance(value, str):
        if SECRET_VALUE.search(value):
            return "<redacted>"
        if len(value) > MAX_SHOWN:
            return value[:40] + "..." + fingerprint(value)
    return value


def redact_state(state: dict[str, Any], policy: str) -> dict[str, Any] | None:
    if policy == "omit":
        return None
    if policy == "hashed":
        return {k: fingerprint(v) for k, v in state.items()}
    return {k: _redact(v, k) for k, v in state.items()}
