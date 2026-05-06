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
from scoopy_logging import log, log_error
from skill_ghl_send_message import ghl_send_message
from skill_ghl_add_tag import ghl_add_tag
from skill_ghl_remove_tag import ghl_remove_tag
from skill_ghl_create_task import ghl_create_task
from skill_ghl_field_update import ghl_field_update
from skill_ghl_update_task import ghl_update_task
from skill_mem0_persist import mem0_persist


SKILL_REGISTRY: dict[str, Any] = {
    "ghl_send_message": ghl_send_message,
    "ghl_add_tag": ghl_add_tag,
    "ghl_remove_tag": ghl_remove_tag,
    "ghl_create_task": ghl_create_task,
    "ghl_field_update": ghl_field_update,
    "ghl_update_task": ghl_update_task,
    "mem0_persist": mem0_persist,
    # Add: ghl_add_note as those skills are implemented.
    #
    # NOTE: the GHL tasks update endpoint is
    # `PUT /contacts/{contactId}/tasks/{taskId}` — contact-scoped only.
    # There is NO top-level `/tasks/{taskId}` endpoint. Every task op
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
    pending = card.get("pending_actions", [])
    log(
        "approval_consumed",
        token_prefix=token[:6] if isinstance(token, str) else None,
        approver=approver,
        action_count=len(pending),
    )
    results: list[dict[str, Any]] = []
    for action in pending:
        skill_name = action.get("skill")
        skill = SKILL_REGISTRY.get(skill_name)
        if skill is None:
            log("skill_call_error", reason=f"unknown skill {skill_name!r}")
            results.append({"status": "error", "reason": f"unknown skill {skill_name!r}"})
            continue
        kwargs = dict(action.get("args", {}))
        kwargs.update({
            "client": client,
            "reasoning": card.get("reasoning", ""),
            "approver": approver,
        })
        log("skill_call", name=skill_name, approver=approver)
        try:
            result = skill(**kwargs)
            results.append(result)
            status = result.get("status") if isinstance(result, dict) else None
            log("skill_result", name=skill_name, status=status or "success")
        except Exception as e:
            log_error("skill_result", e, name=skill_name, status="error")
            results.append({"status": "error", "reason": f"{skill_name} raised {type(e).__name__}: {e}"})
    return results
