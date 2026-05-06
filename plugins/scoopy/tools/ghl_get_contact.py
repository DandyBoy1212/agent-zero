"""ghl_get_contact Tool — fetch full contact payload by id."""
from __future__ import annotations
import sys
import pathlib
import json

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skills_ghl_get import ghl_get_contact as _get_contact_helper
from ghl_client import GhlClient
from scoopy_logging import log, log_error


class GhlGetContact(Tool):
    """Read full contact details (custom fields, tags, basic info)."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="ghl_get_contact", args_keys=",".join(sorted(args.keys())))
        contact_id = args.get("contact_id") or kwargs.get("contact_id")

        if not contact_id:
            log("tool_result", name="ghl_get_contact", outcome="missing_contact_id")
            return Response(
                message="error: ghl_get_contact requires contact_id",
                break_loop=False,
            )

        try:
            client = GhlClient()
            payload = _get_contact_helper(client=client, contact_id=contact_id)
        except Exception as e:
            log_error("tool_result", e, name="ghl_get_contact", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)

        log("tool_result", name="ghl_get_contact", outcome="success")
        msg = f"Contact {contact_id}:\n" + json.dumps(payload, indent=2, default=str)
        return Response(message=msg, break_loop=False)
