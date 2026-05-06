"""ghl_remove_tag skill: remove a tag from a GHL contact → log auto-note.

Approval-gated: only called by execute_with_approval after a valid token is consumed.
"""
from __future__ import annotations
from typing import Any
from auto_note import post_auto_note


def ghl_remove_tag(
    *,
    client,
    contact_id: str,
    tag_name: str,
    reasoning: str,
    approver: str,
) -> dict[str, Any]:
    resp = client.delete(f"/contacts/{contact_id}/tags", payload={"tags": [tag_name]})
    if resp.status_code in (200, 201):
        post_auto_note(
            client=client,
            contact_id=contact_id,
            action_name="ghl_remove_tag",
            reason=reasoning,
            approver=approver,
            result=f"success: tag={tag_name}",
            payload_summary=f"Removed tag: {tag_name}",
        )
        return {"status": "success", "tag": tag_name}
    post_auto_note(
        client=client,
        contact_id=contact_id,
        action_name="ghl_remove_tag",
        reason=reasoning,
        approver=approver,
        result=f"error: status={resp.status_code}",
    )
    return {"status": "error", "code": resp.status_code, "body": resp.text}
