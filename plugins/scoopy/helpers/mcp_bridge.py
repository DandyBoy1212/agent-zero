"""mcp_bridge — HTTP client for the Scoop Patrol MCP server on li-am-1.

One doorway for everything Scoopy asks of the automation server: a JSON-RPC
tools/call POST with Scoopy's own bearer token. The server authenticates the
token, authorises the tool, runs it, and logs every call and refusal to
skill_gap_reports itself, so nothing here needs to log for compliance —
scoopy_logging lines are operator convenience only.

Configuration, in order:

  1. usr/.env on the persistent disk / process env:
         SCOOP_MCP_URL      e.g. https://<li-am-1 host>/mcp
         MCP_TOKEN_SCOOPY   Scoopy's own bearer token
  2. The shared Firestore doc service_config/scoopy_mcp, which li-am-1
     publishes at ITS boot from its own env (see the automation repo's
     execution/mcp_token_handoff.py). Machine-to-machine handoff: no human
     carries the token between two dashboards, and revoking it in li-am-1's
     Render env clears the doc on li-am-1's next boot. Cached per process
     after the first successful read.

Unconfigured is a loud McpBridgeError at call time, never a silent no-op:
a tool that cannot reach the server must say so in-band.

READ_TOOLS run directly from the scoop_patrol tool. WRITE_TOOLS are refused
there in code and only ever execute through skill_mcp_action, which the
dispatcher runs AFTER an owner approves the card. Keeping the split here, in
one frozenset pair, means the tool and the skill cannot drift apart about
which side of the line a tool sits on.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from scoopy_logging import log, log_error

READ_TOOLS = frozenset({
    "server.health",
    "customers.state",
    "customers.find",
    "routes.get",
    "conversations.unread",
    "billing.preview",
})

WRITE_TOOLS = frozenset({
    "billing.apply",
    "messages.send",
    "service.lifecycle",
    "service.change_day",
    "customers.update_inert",
})


class McpBridgeError(Exception):
    """The MCP call could not be made or the server refused/failed it."""


_FIRESTORE_CONFIG_CACHE: tuple[str, str] | None = None


def _config_from_firestore() -> tuple[str, str] | None:
    """The doc li-am-1 publishes for us; cached after the first good read."""
    global _FIRESTORE_CONFIG_CACHE
    if _FIRESTORE_CONFIG_CACHE is not None:
        return _FIRESTORE_CONFIG_CACHE
    try:
        from firestore_client import _build_client
        client = _build_client()
        if client is None:
            return None
        snap = client.collection("service_config").document("scoopy_mcp").get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        url, token = data.get("url"), data.get("token")
        if url and token:
            _FIRESTORE_CONFIG_CACHE = (str(url).rstrip("/"), str(token))
            log("mcp_config_from_firestore", url=str(url))
            return _FIRESTORE_CONFIG_CACHE
    except Exception as e:
        log_error("mcp_config_firestore_failed", e)
    return None


def _config() -> tuple[str, str]:
    url = token = None
    try:
        from helpers.dotenv import get_dotenv_value
        url = get_dotenv_value("SCOOP_MCP_URL")
        token = get_dotenv_value("MCP_TOKEN_SCOOPY")
    except Exception:
        pass
    url = url or os.getenv("SCOOP_MCP_URL")
    token = token or os.getenv("MCP_TOKEN_SCOOPY")
    if url and token:
        return url.rstrip("/"), token
    from_fs = _config_from_firestore()
    if from_fs:
        return from_fs
    raise McpBridgeError(
        "scoop-patrol MCP is not configured: no SCOOP_MCP_URL/MCP_TOKEN_SCOOPY "
        "in usr/.env and no service_config/scoopy_mcp doc in Firestore (does "
        "li-am-1 have MCP_TOKEN_SCOOPY set, and has it booted since?)"
    )


def call_mcp(
    tool: str,
    arguments: dict[str, Any] | None = None,
    on_behalf_of: str | None = None,
    timeout: int = 300,
) -> Any:
    """POST one tools/call and return the tool's structured result.

    Raises McpBridgeError for BOTH failure channels the protocol has:
    a JSON-RPC error object (bad request, unknown tool) and an
    isError=true tool result (the tool ran and refused or raised). The
    caller gets the server's own message either way, redacted server-side.
    """
    import requests

    url, token = _config()
    args = dict(arguments or {})
    if on_behalf_of:
        # Log attribution only; the server's identity layer forbids it from
        # widening what the token may call.
        args["_on_behalf_of"] = on_behalf_of

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
    except Exception as e:
        log_error("mcp_call_failed", e, tool=tool)
        raise McpBridgeError(f"could not reach the scoop-patrol server: {e}") from e

    if resp.status_code == 401:
        raise McpBridgeError("the scoop-patrol server rejected Scoopy's token (401)")
    if resp.status_code >= 400:
        raise McpBridgeError(f"the scoop-patrol server answered HTTP {resp.status_code}")

    body = resp.json()
    if body.get("error"):
        raise McpBridgeError(f"protocol error: {body['error'].get('message', 'unknown')}")

    result = body.get("result") or {}
    if result.get("isError"):
        content = result.get("content") or [{}]
        raise McpBridgeError(content[0].get("text", "tool call failed"))

    log("mcp_call", tool=tool, on_behalf_of=on_behalf_of or "")
    if "structuredContent" in result:
        return result["structuredContent"]
    content = result.get("content") or [{}]
    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except Exception:
        return {"text": text}
