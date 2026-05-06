"""ghl_create_task skill: create a task on a GHL contact → log auto-note.

For [REPLY]-titled tasks, also adds the `scoopy-watching` tag so the agent
knows to monitor the contact for incoming replies. Only one auto-note is
posted per logical action (the watching-tag is mentioned in the summary,
not separately noted).

Approval-gated: only called by execute_with_approval after a valid token is consumed.
"""
from __future__ import annotations
import os
from typing import Any
from auto_note import post_auto_note


def ghl_create_task(
    *,
    client,
    contact_id: str,
    title: str,
    body: str,
    due_date: str,
    reasoning: str,
    approver: str,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    if assigned_to is None:
        assigned_to = os.getenv("SCOOPY_USER_ID")
    payload = {
        "title": title,
        "body": body,
        "dueDate": due_date,
        "completed": False,
        "assignedTo": assigned_to,
    }
    resp = client.post(f"/contacts/{contact_id}/tasks", payload=payload)
    if resp.status_code in (200, 201):
        resp_body = resp.json() if callable(getattr(resp, "json", None)) else {}
        task_id = resp_body.get("id") or resp_body.get("taskId") or "unknown"
        added_watching_tag = False
        if title.startswith("[REPLY]"):
            # Add scoopy-watching tag without a separate auto-note.
            client.post(f"/contacts/{contact_id}/tags", payload={"tags": ["scoopy-watching"]})
            added_watching_tag = True
        summary = f"Created task: {title} (due {due_date}, assigned {assigned_to})"
        if added_watching_tag:
            summary += " | also added tag: scoopy-watching"
        post_auto_note(
            client=client,
            contact_id=contact_id,
            action_name="ghl_create_task",
            reason=reasoning,
            approver=approver,
            result=f"success: task_id={task_id}",
            payload_summary=summary,
        )
        return {"status": "success", "task_id": task_id, "title": title}
    post_auto_note(
        client=client,
        contact_id=contact_id,
        action_name="ghl_create_task",
        reason=reasoning,
        approver=approver,
        result=f"error: status={resp.status_code}",
    )
    return {"status": "error", "code": resp.status_code, "body": resp.text}
