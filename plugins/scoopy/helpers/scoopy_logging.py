"""Structured logging for the Scoopy plugin.

stdout-only by default — Render and Cloud Run capture stdout. JSON format
makes log search and filtering work without extra infra. Adds the basic
contextual fields every event needs.
"""
from __future__ import annotations
import json
import logging
import os
import sys
import time
import traceback as tb
from typing import Any
from datetime import datetime, timezone

_LOGGER = logging.getLogger("scoopy")
_LOGGER.setLevel(os.getenv("SCOOPY_LOG_LEVEL", "INFO").upper())

if not _LOGGER.handlers:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(h)
    _LOGGER.propagate = False


def _redact(value: Any) -> Any:
    """Drop obvious secret values. Add patterns as discovered."""
    if isinstance(value, str):
        if value.startswith("sk-") or value.startswith("pit-") or value.startswith("Bearer "):
            return "<redacted>"
    return value


def log(event: str, level: str = "info", **fields: Any) -> None:
    """Emit one structured log line."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **{k: _redact(v) for k, v in fields.items()},
    }
    line = json.dumps(payload, default=str, separators=(",", ":"))
    getattr(_LOGGER, level.lower(), _LOGGER.info)(line)


def log_error(event: str, exc: BaseException | None = None, **fields: Any) -> None:
    """Emit an error line with traceback."""
    if exc is not None:
        fields["error_type"] = type(exc).__name__
        fields["error_message"] = str(exc)
        fields["traceback"] = tb.format_exc()
    log(event, level="error", **fields)


def timed(event: str, **base_fields: Any):
    """Context manager for timing a block. Logs start + end with duration_ms.

    Usage:
        with timed("ghl_api", method="POST", path="/conversations/messages") as ctx:
            resp = client.post(...)
            ctx["status"] = resp.status_code
    """
    class _Timed:
        def __init__(self):
            self.fields = dict(base_fields)
        def __enter__(self):
            self._t0 = time.monotonic()
            return self.fields
        def __exit__(self, etype, evalue, _tb):
            self.fields["duration_ms"] = int((time.monotonic() - self._t0) * 1000)
            if etype is not None:
                log_error(event, evalue, **self.fields)
            else:
                log(event, **self.fields)
            return False
    return _Timed()
