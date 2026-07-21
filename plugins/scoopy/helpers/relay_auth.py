"""Shared API-key gate for Scoopy's HTTP endpoints.

Every endpoint under plugins/scoopy/api/ historically declared
requires_auth, requires_api_key and requires_csrf all False. For the
approve and reject endpoints that is defensible, because they carry an
unguessable capability token. For scoopy_inbox and scoopy_settings_set it
meant anyone who knew the URL could read pending approvals or switch
auto-approve on. This module is the gate those endpoints now call.

Why not Agent Zero's built-in requires_api_key decorator: it checks
settings["mcp_server_token"], and settings.json lives under usr/, which is
wiped on every restart while the Render service has no disk. An
environment variable survives restarts.

Fails closed. An unset key denies every request rather than allowing them.
"""
from __future__ import annotations

import hmac
import os

ENV_VAR = "SCOOPY_RELAY_KEY"


class RelayAuthError(Exception):
    """Raised when a request does not carry a valid relay key."""


def check_relay_key(provided: str | None) -> None:
    """Return None if `provided` matches the configured key, else raise.

    Uses a constant-time comparison so the response time does not leak how
    much of the key was correct.
    """
    expected = os.getenv(ENV_VAR)
    if not expected:
        raise RelayAuthError(f"{ENV_VAR} not configured")
    if not provided:
        raise RelayAuthError("missing key")
    # Compare UTF-8 encoded bytes rather than str: hmac.compare_digest raises
    # TypeError for non-ASCII str operands, which would otherwise escape as
    # an unhandled 500 instead of the RelayAuthError callers expect.
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise RelayAuthError("invalid key")
    return None
