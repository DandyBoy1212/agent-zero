"""ghl_add_tag skill: add a tag to a GHL contact → log auto-note.

Approval-gated: only called by execute_with_approval after a valid token is consumed.
"""
from __future__ import annotations
from typing import Any
from auto_note import post_auto_note
from scoopy_logging import log


def ghl_add_tag(
    *,
    client,
    contact_id: str,
    tag_name: str,
    reasoning: str,
    approver: str,
) -> dict[str, Any]:
    log("skill_helper_call", name="ghl_add_tag", contact_id=contact_id, tag=tag_name)
    resp = client.post(f"/contacts/{contact_id}/tags", payload={"tags": [tag_name]})
    if resp.status_code in (200, 201):
        post_auto_note(
            client=client,
            contact_id=contact_id,
            action_name="ghl_add_tag",
            reason=reasoning,
            approver=approver,
            result=f"success: tag={tag_name}",
            payload_summary=f"Added tag: {tag_name}",
        )
        log("skill_helper_result", name="ghl_add_tag", status="success", tag=tag_name)
        return {"status": "success", "tag": tag_name}
    post_auto_note(
        client=client,
        contact_id=contact_id,
        action_name="ghl_add_tag",
        reason=reasoning,
        approver=approver,
        result=f"error: status={resp.status_code}",
    )
    log("skill_helper_result", name="ghl_add_tag", status="error", code=resp.status_code)
    return {"status": "error", "code": resp.status_code, "body": resp.text}
