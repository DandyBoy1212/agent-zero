"""execute_with_approval — runs queued actions if the token validates.

Looks up each pending_action's skill in SKILL_REGISTRY and calls it with
client, reasoning, approver, and any per-action args. Each skill is
responsible for its own auto-note. Token is single-use (consumed before
any skill runs).

Add new write skills to SKILL_REGISTRY as they are implemented.
"""
from __future__ import annotations
from typing import Any
from approval import ApprovalStore, default_store
from skill_ghl_send_message import ghl_send_message


SKILL_REGISTRY: dict[str, Any] = {
    "ghl_send_message": ghl_send_message,
    # Add: ghl_remove_tag, ghl_create_task, ghl_update_task, ghl_field_update,
    # ghl_add_note, mem0_persist as those skills are implemented.
    #
    # NOTE for future ghl_update_task implementer: the GHL tasks update
    # endpoint is `PUT /contacts/{contactId}/tasks/{taskId}` — contact-scoped
    # only. There is NO top-level `/tasks/{taskId}` endpoint. Every task op
    # (list, create, update, complete, delete) lives under the contact path.
    # Cite: highlevel-api-docs/apps/contacts.json lines 392-492.
}


def execute_with_approval(
    *,
    store: ApprovalStore | None = None,
    token: str,
    approver: str,
    client: Any,
) -> list[dict[str, Any]]:
    s = store if store is not None else default_store
    card = s.consume(token)  # raises ApprovalError if bad/expired
    results: list[dict[str, Any]] = []
    for action in card.get("pending_actions", []):
        skill_name = action.get("skill")
        skill = SKILL_REGISTRY.get(skill_name)
        if skill is None:
            results.append({"status": "error", "reason": f"unknown skill {skill_name!r}"})
            continue
        kwargs = dict(action.get("args", {}))
        kwargs.update({
            "client": client,
            "reasoning": card.get("reasoning", ""),
            "approver": approver,
        })
        try:
            results.append(skill(**kwargs))
        except Exception as e:
            results.append({"status": "error", "reason": f"{skill_name} raised {type(e).__name__}: {e}"})
    return results
