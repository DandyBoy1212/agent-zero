"""notify_owner — the agent's path for proposing actions.

Modes:
- auto-approve (SCOOPY_AUTO_APPROVE=1, default): immediately runs the
  pending_actions and returns results. Auto-notes still fire on each write.
- approval-required (SCOOPY_AUTO_APPROVE=0): queues a card; owner clicks
  Approve in the inbox; dispatcher then runs the actions.

The same call signature works for both modes. Switch the env var per
deployment — auto-approve for trusted day-to-day, approval-required for
prospect demos / when "showing the safety story" matters.
"""
from __future__ import annotations
import os
from typing import Any
from approval import ApprovalStore, default_store
from scoopy_logging import log, log_error


VALID_ACTION_TYPES = {
    "in_scope", "drift", "escalation", "create_task", "memory_candidate",
}


def _auto_approve_enabled() -> bool:
    return os.getenv("SCOOPY_AUTO_APPROVE", "1").strip() not in ("", "0", "false", "False", "no", "NO")


def notify_owner(
    *,
    store: ApprovalStore | None = None,
    contact_id: str,
    draft: str,
    reasoning: str,
    action_type: str,
    pending_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(
            f"action_type must be one of {sorted(VALID_ACTION_TYPES)}, got {action_type!r}"
        )
    s = store if store is not None else default_store
    card = {
        "contact_id": contact_id,
        "draft": draft,
        "reasoning": reasoning,
        "action_type": action_type,
        "pending_actions": list(pending_actions),
    }
    token = s.issue(card=card)
    log("notify_owner_queued",
        action_type=action_type,
        pending_count=len(pending_actions),
        skill_names=",".join(a.get("skill", "?") for a in pending_actions),
        contact_id=contact_id,
        auto_approve=_auto_approve_enabled())

    if _auto_approve_enabled():
        # Run immediately. Import here to avoid circular import (dispatcher imports skills).
        from dispatcher import execute_with_approval
        from ghl_client import GhlClient
        try:
            client = GhlClient()
            results = execute_with_approval(
                store=s, token=token, approver="scoopy_auto", client=client,
            )
            log("notify_owner_auto_executed",
                action_type=action_type,
                results_count=len(results),
                statuses=",".join(r.get("status", "?") for r in results))
            return {
                "approval_token": token,
                "status": "executed",
                "auto_approved": True,
                "results": results,
            }
        except Exception as e:
            log_error("notify_owner_auto_execute_failed", exc=e, action_type=action_type)
            return {
                "approval_token": token,
                "status": "auto_execute_failed",
                "auto_approved": True,
                "error": str(e),
            }

    return {"approval_token": token, "status": "queued", "auto_approved": False}
