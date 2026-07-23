"""scoop_patrol Tool — Scoopy's window onto the automation server's MCP tools.

Reads execute immediately and return the server's structured answer. Writes
are REFUSED here in code, not in prompt: the only way a write reaches the
server is a notify_owner card whose pending_actions carry
{"skill": "mcp_action", ...}, which the dispatcher runs after the owner
approves. A model that forgets the rule hits this wall and is told, in the
refusal, exactly how to do it properly.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from mcp_bridge import READ_TOOLS, WRITE_TOOLS, McpBridgeError, call_mcp
from scoopy_logging import log


class ScoopPatrol(Tool):
    """Query the Scoop Patrol automation server (customers, routes, billing)."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        tool = args.get("tool") or kwargs.get("tool") or ""
        arguments = args.get("arguments")
        if arguments is None:
            arguments = kwargs.get("arguments") or {}
        log("tool_invoked", name="scoop_patrol", mcp_tool=tool)

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception:
                return Response(
                    message="error: arguments must be an object or JSON-encoded object",
                    break_loop=False,
                )
        if not isinstance(arguments, dict):
            return Response(message="error: arguments must be an object", break_loop=False)

        if tool in WRITE_TOOLS:
            return Response(
                message=(
                    f"refused: {tool} is a WRITE and never runs directly. Queue it for "
                    f"owner approval instead: call notify_owner with pending_actions="
                    f'[{{"skill": "mcp_action", "args": {{"tool": "{tool}", '
                    f'"arguments": {{...}}}}}}]. For billing.apply, run billing.preview '
                    f"first and put its outcome in the draft so the owner sees exactly "
                    f"what will happen before saying yes."
                ),
                break_loop=False,
            )
        if tool not in READ_TOOLS:
            return Response(
                message=(
                    f"error: unknown scoop-patrol tool {tool!r}. Reads: "
                    f"{', '.join(sorted(READ_TOOLS))}. Writes "
                    f"({', '.join(sorted(WRITE_TOOLS))}) go through notify_owner "
                    f"as mcp_action."
                ),
                break_loop=False,
            )

        try:
            # call_mcp does blocking HTTP; keep it off the event loop.
            result = await asyncio.to_thread(call_mcp, tool, arguments)
        except McpBridgeError as e:
            log("tool_result", name="scoop_patrol", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)

        log("tool_result", name="scoop_patrol", outcome="ok")
        text = json.dumps(result, ensure_ascii=False, default=str)
        # Guard the context window: customers.find over a broad filter can be
        # large. 20k chars is roomy for every legitimate single answer.
        if len(text) > 20000:
            text = text[:20000] + "… (truncated; narrow the query)"
        return Response(message=text, break_loop=False)
