"""mem0_save_candidate Tool — queue a memory candidate for owner curation.

Wraps the helper of the same name. The helper calls notify_owner under the
hood with action_type="memory_candidate" and a pending mem0_persist action,
so the SAVE itself is approval-gated via the standard inbox flow.
"""
from __future__ import annotations
import sys
import pathlib

# Inject our helpers/ onto sys.path (same pattern as notify_owner.py)
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_mem0_save_candidate import mem0_save_candidate as _save_candidate_helper
from scoopy_logging import log, log_error


class Mem0SaveCandidate(Tool):
    """Queue a fact for owner approval before persisting to Mem0."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="mem0_save_candidate", args_keys=",".join(sorted(args.keys())))
        contact_id = args.get("contact_id") or kwargs.get("contact_id")
        namespace = args.get("namespace") or kwargs.get("namespace")
        fact = args.get("fact") or kwargs.get("fact")
        why_save = args.get("why_save") or kwargs.get("why_save")

        if not contact_id:
            return Response(
                message="error: mem0_save_candidate requires contact_id",
                break_loop=False,
            )
        if not namespace:
            return Response(
                message="error: mem0_save_candidate requires namespace",
                break_loop=False,
            )
        if not fact:
            return Response(
                message="error: mem0_save_candidate requires fact",
                break_loop=False,
            )
        if not why_save:
            return Response(
                message="error: mem0_save_candidate requires why_save",
                break_loop=False,
            )

        try:
            result = _save_candidate_helper(
                contact_id=contact_id,
                namespace=namespace,
                fact=fact,
                why_save=why_save,
            )
        except ValueError as e:
            log_error("tool_result", e, name="mem0_save_candidate", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)
        log("tool_result", name="mem0_save_candidate", outcome="queued")

        msg = (
            "Memory candidate queued for owner approval.\n"
            f"approval_token: {result['approval_token']}\n"
            f"status: {result['status']}\n"
            f"namespace: {namespace}\n"
            "Wait for the owner to approve via the inbox; mem0_persist runs "
            "only after approval."
        )
        # break_loop=True: a curation card is queued; this turn is done.
        return Response(message=msg, break_loop=True)
