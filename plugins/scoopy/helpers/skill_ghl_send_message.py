"""ghl_send_message skill: send SMS via GHL → log auto-note.

Mirrors the convention from
`agentic-workflows-skill/execution/create_scheduled_invoice.py::send_conversation_message`.
Approval-gated: only called by execute_with_approval after a valid token is consumed.
The agent CANNOT call this directly.
"""
from __future__ import annotations
from typing import Any
from auto_note import post_auto_note


def ghl_send_message(
    *,
    client,
    contact_id: str,
    message: str,
    reasoning: str,
    approver: str,
) -> dict[str, Any]:
    payload = {"type": "SMS", "contactId": contact_id, "message": message}
    resp = client.post("/conversations/messages", payload=payload)
    if resp.status_code in (200, 201):
        body = resp.json()
        message_id = body.get("messageId") or body.get("id") or "unknown"
        post_auto_note(
            client=client,
            contact_id=contact_id,
            action_name="ghl_send_message",
            reason=reasoning,
            approver=approver,
            result=f"success: msg_id={message_id}",
            payload_summary=f"Sent: {message[:200]}",
        )
        return {"status": "success", "message_id": message_id}
    post_auto_note(
        client=client,
        contact_id=contact_id,
        action_name="ghl_send_message",
        reason=reasoning,
        approver=approver,
        result=f"error: status={resp.status_code}",
    )
    return {"status": "error", "code": resp.status_code, "body": resp.text}
