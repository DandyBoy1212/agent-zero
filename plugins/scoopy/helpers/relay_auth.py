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


def check_relay_key(provided: object) -> None:
    """Validate `provided` against the configured relay key.

    Accepts anything, but only ever succeeds for a non-empty `str` that
    matches SCOOPY_RELAY_KEY exactly (constant-time comparison). Every other
    input -- wrong key, missing key, unset/empty configured key, or a
    `provided` that is not a non-empty `str` (None, bytes, list, int, or any
    other object a header multidict might hand back) -- raises
    RelayAuthError. No other exception type ever escapes this function.
    """
    expected = os.getenv(ENV_VAR)
    if not expected:
        raise RelayAuthError(f"{ENV_VAR} not configured")
    # Validate shape at the boundary rather than reacting to each failure
    # mode a malformed input can cause downstream (TypeError from
    # hmac.compare_digest on non-ASCII str, UnicodeEncodeError from encoding
    # a lone surrogate, AttributeError from calling .encode on something
    # that isn't a str at all, e.g. bytes/list/int from a misbehaving
    # header multidict). Anything that is not a non-empty str is simply not
    # a valid key, full stop -- never coerce it into something comparable.
    if not isinstance(provided, str) or not provided:
        raise RelayAuthError("provided key is not a non-empty string")
    # Compare UTF-8 encoded bytes rather than str: hmac.compare_digest raises
    # TypeError for non-ASCII str operands, which would otherwise escape as
    # an unhandled 500 instead of the RelayAuthError callers expect.
    #
    # Encoding itself can also raise: WSGI/ASGI servers commonly decode raw
    # header bytes with surrogateescape, so a header carrying invalid UTF-8
    # arrives as a str containing a lone surrogate (e.g. "\udc80"), and
    # str.encode("utf-8") rejects that with UnicodeEncodeError. Treat a key
    # that cannot even be encoded as simply invalid, same as any other
    # mismatch, rather than letting the encoding error escape as a 500.
    try:
        provided_bytes = provided.encode("utf-8")
        expected_bytes = expected.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RelayAuthError("key not encodable as utf-8") from exc
    if not hmac.compare_digest(provided_bytes, expected_bytes):
        raise RelayAuthError("invalid key")
    return None
