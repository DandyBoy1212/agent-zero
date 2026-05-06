"""mem0_search Tool — read-only memory lookup.

Wraps the helper of the same name. Returns memories as a compact JSON list
so the agent can reason over context before drafting a reply.
"""
from __future__ import annotations
import sys
import pathlib
import json

# Inject our helpers/ onto sys.path (same pattern as notify_owner.py)
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_mem0_search import mem0_search as _search_helper
from scoopy_logging import log, log_error


class Mem0Search(Tool):
    """Search Scoopy's Mem0 memory for context before drafting a reply."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="mem0_search", args_keys=",".join(sorted(args.keys())))
        namespace = args.get("namespace") or kwargs.get("namespace")
        query = args.get("query") or kwargs.get("query")
        limit = args.get("limit") or kwargs.get("limit", 5)

        if not namespace:
            return Response(
                message="error: mem0_search requires namespace",
                break_loop=False,
            )
        if not query:
            return Response(
                message="error: mem0_search requires query",
                break_loop=False,
            )
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 5

        try:
            memories = _search_helper(namespace=namespace, query=query, limit=limit)
        except Exception as e:
            log_error("tool_result", e, name="mem0_search", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)
        log("tool_result", name="mem0_search", outcome="success", count=len(memories))

        msg = (
            f"Found {len(memories)} memory(ies) in namespace '{namespace}' "
            f"for query '{query}':\n" + json.dumps(memories, indent=2, default=str)
        )
        # break_loop=False — read tools don't end the agent's reasoning turn.
        return Response(message=msg, break_loop=False)
