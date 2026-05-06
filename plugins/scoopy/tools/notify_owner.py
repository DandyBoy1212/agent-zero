"""notify_owner Tool — the agent's only write path.

The agent calls this with a draft and pending_actions. We call the
underlying helper, which queues an approval card. Owner clicks Approve
in the inbox UI; the dispatcher (execute_with_approval) then runs the
queued actions.
"""
from __future__ import annotations
import os
import sys
import pathlib
import json

# Inject our helpers/ onto sys.path (same pattern as the api/ handlers)
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_notify_owner import notify_owner as _notify_owner_helper
from scoopy_logging import log


class NotifyOwner(Tool):
    """Queue an approval card for owner review.

    The agent's ONLY write path. Direct writes are not permitted; instead
    queue actions here and wait for the owner to approve via the inbox.
    """

    async def execute(self, **kwargs) -> Response:
        # Tool args come via self.args (Agent Zero convention); also accept
        # kwargs as a defensive fallback.
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="notify_owner", args_keys=",".join(sorted(args.keys())))
        contact_id = args.get("contact_id") or kwargs.get("contact_id")
        draft = args.get("draft") or kwargs.get("draft", "")
        reasoning = args.get("reasoning") or kwargs.get("reasoning", "")
        action_type = args.get("action_type") or kwargs.get("action_type", "")
        pending_actions = args.get("pending_actions")
        if pending_actions is None:
            pending_actions = kwargs.get("pending_actions", [])

        if not contact_id:
            return Response(
                message="error: notify_owner requires contact_id",
                break_loop=False,
            )
        if not action_type:
            return Response(
                message="error: notify_owner requires action_type",
                break_loop=False,
            )

        # If pending_actions came in as a JSON string, parse it
        if isinstance(pending_actions, str):
            try:
                pending_actions = json.loads(pending_actions)
            except Exception:
                return Response(
                    message="error: pending_actions must be a list or a JSON-encoded list",
                    break_loop=False,
                )
        if not isinstance(pending_actions, list):
            return Response(
                message="error: pending_actions must be a list",
                break_loop=False,
            )

        try:
            result = _notify_owner_helper(
                contact_id=contact_id,
                draft=draft,
                reasoning=reasoning,
                action_type=action_type,
                pending_actions=pending_actions,
            )
        except ValueError as e:
            return Response(message=f"error: {e}", break_loop=False)

        inbox_base = os.getenv("SCOOPY_AGENT_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""
        inbox_url = (
            f"{inbox_base.rstrip('/')}/api/plugins/scoopy/scoopy_inbox"
            if inbox_base
            else "/api/plugins/scoopy/scoopy_inbox"
        )

        log("tool_result", name="notify_owner", outcome="queued")
        msg = (
            f"✅ Drafted — queued for your approval.\n\n"
            f"Open the inbox to approve or edit: {inbox_url}\n\n"
            f"approval_token: {result['approval_token']}"
        )
        # break_loop=True: queuing a card ends this reasoning turn. The
        # dispatcher runs the actions only after the owner approves; the
        # agent should not keep iterating.
        return Response(message=msg, break_loop=True)
