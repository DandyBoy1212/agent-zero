"""ghl_search_contact Tool — read-only contact lookup for the agent.

Wraps the helper of the same name. Returns a compact JSON list of
matching contacts so the agent can pick the right id by context.
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
from skill_ghl_search_contact import ghl_search_contact as _search_helper
from ghl_client import GhlClient
from scoopy_logging import log, log_error


class GhlSearchContact(Tool):
    """Find contacts by free-form query (name, phone, email)."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="ghl_search_contact", args_keys=",".join(sorted(args.keys())))
        query = args.get("query") or kwargs.get("query")
        limit = args.get("limit") or kwargs.get("limit", 10)

        if not query:
            return Response(
                message="error: ghl_search_contact requires query",
                break_loop=False,
            )

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10

        try:
            client = GhlClient()
            contacts = _search_helper(client=client, query=query, limit=limit)
        except Exception as e:
            log_error("tool_result", e, name="ghl_search_contact", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)
        log("tool_result", name="ghl_search_contact", outcome="success", count=len(contacts))

        # Trim to the fields the agent actually needs to pick a contact.
        compact = [
            {
                "id": c.get("id"),
                "name": c.get("contactName")
                or f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
                "email": c.get("email"),
                "phone": c.get("phone"),
                "tags": c.get("tags", []),
            }
            for c in contacts
        ]
        msg = (
            f"Found {len(compact)} contact(s) matching '{query}':\n"
            + json.dumps(compact, indent=2)
        )
        # break_loop=False — read tools don't end the agent's reasoning turn.
        return Response(message=msg, break_loop=False)
