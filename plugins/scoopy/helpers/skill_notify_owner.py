"""notify_owner — the agent's path for proposing actions.

Modes:
- approval-required (SCOOPY_AUTO_APPROVE unset or 0, default): queues a card;
  owner clicks Approve in the inbox; dispatcher then runs the actions.
- auto-approve (SCOOPY_AUTO_APPROVE=1): immediately runs the pending_actions
  and returns results. Auto-notes still fire on each write.

The same call signature works for both modes. Switch the env var per
deployment — approval-required is stage one of the trust ladder (everything
asks) and is the default; auto-approve is an opt-in for trusted day-to-day
once that trust is earned.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
from approval import ApprovalStore, default_store
from scoopy_logging import log, log_error


VALID_ACTION_TYPES = {
    "in_scope", "drift", "escalation", "create_task", "memory_candidate",
}

VALID_TRIGGER_CONTEXTS = {"asked", "reactive", "scheduled", "unknown"}

# usr/ is the persistent disk mount (Render: /a0/usr); tmp/ is wiped on every
# restart. This setting used to live in tmp/, which meant turning auto-approve
# off silently reverted to on after every restart.
_RUNTIME_FILE = Path("usr/scoopy_runtime.json")


def _auto_approve_enabled() -> bool:
    # Runtime file overrides env var if present
    try:
        if _RUNTIME_FILE.exists():
            data = json.loads(_RUNTIME_FILE.read_text(encoding="utf-8"))
            if "auto_approve" in data:
                return bool(data["auto_approve"])
    except Exception:
        pass
    # Stage one of the trust ladder is everything-asks: an unset or falsy
    # SCOOPY_AUTO_APPROVE means auto-approve is OFF by default. Opt in
    # explicitly with SCOOPY_AUTO_APPROVE=1 once that trust is earned.
    return os.getenv("SCOOPY_AUTO_APPROVE", "0").strip() in ("1", "true", "True", "yes", "YES")


def notify_owner(
    *,
    store: ApprovalStore | None = None,
    contact_id: str,
    draft: str,
    reasoning: str,
    action_type: str,
    pending_actions: list[dict[str, Any]],
    summary: str = "",
    detail: str = "",
    customer_name: str = "",
    trigger_context: str = "unknown",
    conversation_id: str = "",
) -> dict[str, Any]:
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(
            f"action_type must be one of {sorted(VALID_ACTION_TYPES)}, got {action_type!r}"
        )
    if trigger_context not in VALID_TRIGGER_CONTEXTS:
        raise ValueError(
            f"trigger_context must be one of {sorted(VALID_TRIGGER_CONTEXTS)}, "
            f"got {trigger_context!r}"
        )
    s = store if store is not None else default_store
    card = {
        "contact_id": contact_id,
        "draft": draft,
        "reasoning": reasoning,
        "action_type": action_type,
        "pending_actions": list(pending_actions),
        # The human-facing face of the card. `draft` is a proposed customer
        # message and was being reused as a description for cards that are not
        # messages, which renders a payload or a blank. A person cannot consent
        # to a payload.
        "summary": summary,
        "detail": detail,
        "customer_name": customer_name,
        # Recorded now, read by nobody yet. Nearly free at write time and
        # awkward to backfill, and the approval grid in the spec needs it.
        "trigger_context": trigger_context,
        # Which conversation raised this. Without it the chat surface shows
        # every pending card on every thread, because a card is raised against
        # a customer and there was no link back to a chat. Observed 2026-07-22:
        # a card raised by an API test appeared inside Liam D's conversation
        # about something else entirely, and read as a random suggestion.
        # Empty means "raised outside a chat" (a webhook, a cron), and those
        # must still show everywhere, because a hidden card is an action that
        # never happens.
        "conversation_id": conversation_id,
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
