"""notify_owner — the ONLY path the agent has to queue write actions.

The agent calls this with a draft and a list of pending_actions. We issue
an approval token and store the card. The inbox UI shows the card; on
Approve, the dispatcher consumes the token and runs each action.

action_type is informational for the UI:
    - in_scope: customer reply matches the active task scope; agent has a draft
    - drift: reply is out of task scope; agent drafted a holding response
    - escalation: agent has no useful suggestion; needs owner judgment
    - create_task: agent wants to schedule a future [ACTION] task
    - memory_candidate: agent suggests remembering a fact (curation gate)
"""
from __future__ import annotations
from typing import Any
from approval import ApprovalStore, default_store
from scoopy_logging import log


VALID_ACTION_TYPES = {
    "in_scope", "drift", "escalation", "create_task", "memory_candidate",
}


def notify_owner(
    *,
    store: ApprovalStore | None = None,
    contact_id: str,
    draft: str,
    reasoning: str,
    action_type: str,
    pending_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Queue an approval card. Returns {approval_token, status}.

    The agent calls this; the inbox UI displays the card; on Approve, the
    /agent/approve endpoint calls execute_with_approval(token, ...) which
    runs each pending_action.
    """
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
    skill_names = ",".join(a.get("skill", "") for a in pending_actions)
    log(
        "notify_owner_queued",
        action_type=action_type,
        pending_count=len(pending_actions),
        contact_id=contact_id,
        skill_names=skill_names,
    )
    return {"approval_token": token, "status": "queued"}
