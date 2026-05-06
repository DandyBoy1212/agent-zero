"""ghl_get_tasks_for_contact Tool — list a contact's open tasks."""
from __future__ import annotations
import sys
import pathlib
import json

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skills_ghl_get import ghl_get_tasks_for_contact as _get_tasks_helper
from ghl_client import GhlClient
from scoopy_logging import log, log_error


class GhlGetTasksForContact(Tool):
    """List a contact's open tasks, optionally filtered."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="ghl_get_tasks_for_contact", args_keys=",".join(sorted(args.keys())))
        contact_id = args.get("contact_id") or kwargs.get("contact_id")
        assigned_to_scoopy_only = args.get("assigned_to_scoopy_only")
        if assigned_to_scoopy_only is None:
            assigned_to_scoopy_only = kwargs.get("assigned_to_scoopy_only", False)
        title_prefix = args.get("title_prefix") or kwargs.get("title_prefix")

        if not contact_id:
            return Response(
                message="error: ghl_get_tasks_for_contact requires contact_id",
                break_loop=False,
            )

        # Coerce truthy strings to bool
        if isinstance(assigned_to_scoopy_only, str):
            assigned_to_scoopy_only = assigned_to_scoopy_only.lower() in (
                "1", "true", "yes", "y",
            )

        try:
            client = GhlClient()
            tasks = _get_tasks_helper(
                client=client,
                contact_id=contact_id,
                assigned_to_scoopy_only=bool(assigned_to_scoopy_only),
                title_prefix=title_prefix,
            )
        except Exception as e:
            log_error("tool_result", e, name="ghl_get_tasks_for_contact", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)

        log("tool_result", name="ghl_get_tasks_for_contact", outcome="success", count=len(tasks))
        msg = (
            f"Found {len(tasks)} open task(s) for contact {contact_id}:\n"
            + json.dumps(tasks, indent=2, default=str)
        )
        return Response(message=msg, break_loop=False)
