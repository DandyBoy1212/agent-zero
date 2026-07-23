"""mcp_action skill — executes ONE approved MCP write through the doorway.

Runs only from the dispatcher, which means only after an owner consumed an
approval card. The card's approver is passed to the server as
_on_behalf_of, so skill_gap_reports records which human said yes, and the
server's own gates (billing verification, the messages.send freshness
check) still stand between an approval and the world: an approved card
whose action the server refuses comes back as an error result, never a
silent success.

Restricted to WRITE_TOOLS: reads never need a card, and an approved card
smuggling a read through here would only blur the line the scoop_patrol
tool enforces.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from mcp_bridge import WRITE_TOOLS, McpBridgeError, call_mcp
from scoopy_logging import log, log_error


def mcp_action(
    *,
    tool: str = "",
    arguments: dict[str, Any] | None = None,
    client: Any = None,
    reasoning: str = "",
    approver: str = "",
    **_ignored: Any,
) -> dict[str, Any]:
    if tool not in WRITE_TOOLS:
        return {
            "status": "error",
            "reason": f"mcp_action only runs write tools, got {tool!r}",
        }
    try:
        result = call_mcp(tool, arguments, on_behalf_of=approver or None)
    except McpBridgeError as e:
        log_error("mcp_action_failed", e, tool=tool)
        return {"status": "error", "reason": str(e)}

    # A tool that ran but refused through its gate reports problems; that is
    # a failed action from the approver's point of view, not a success with
    # small print.
    if isinstance(result, dict) and result.get("problems"):
        reasons = "; ".join(
            str(p.get("message", p)) for p in result["problems"]
        )
        log("mcp_action_refused", tool=tool, reasons=reasons[:300])
        return {"status": "error", "reason": reasons, "result": result}

    log("mcp_action_done", tool=tool, approver=approver)
    return {"status": "success", "result": result}
