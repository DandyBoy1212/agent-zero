"""notify_owner Tool — the agent's only write path.

The agent calls this with a draft and pending_actions. We call the
underlying helper, which queues an approval card. Owner clicks Approve
in the inbox UI; the dispatcher (execute_with_approval) then runs the
queued actions.
"""
from __future__ import annotations
import sys
import pathlib
import json

# Inject our helpers/ onto sys.path (same pattern as the api/ handlers)
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_notify_owner import notify_owner as _notify_owner_helper


class NotifyOwner(Tool):
    """Queue an approval card for owner review.

    The agent's ONLY write path. Direct writes are not permitted; instead
    queue actions here and wait for the owner to approve via the inbox.
    """

    async def execute(self, **kwargs) -> Response:
        # Tool args come via self.args (Agent Zero convention); also accept
        # kwargs as a defensive fallback.
        args = getattr(self, "args", {}) or {}
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

        msg = (
            "Card queued for owner approval.\n"
            f"approval_token: {result['approval_token']}\n"
            f"status: {result['status']}\n"
            "Wait for the owner to approve via the inbox. Do not call any "
            "write skill yourself — execute_with_approval is invoked by the "
            "approval endpoint."
        )
        # break_loop=True: queuing a card ends this reasoning turn. The
        # dispatcher runs the actions only after the owner approves; the
        # agent should not keep iterating.
        return Response(message=msg, break_loop=True)
