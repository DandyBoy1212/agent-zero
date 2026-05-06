"""ghl_update_task skill: update a task on a GHL contact → log auto-note.

GHL API: PUT /contacts/{contact_id}/tasks/{task_id} (contact-scoped only —
there is NO top-level /tasks/{task_id} endpoint).

Only fields explicitly provided are sent (None values are omitted) so we
never accidentally overwrite existing fields with empties.

Approval-gated: only called by execute_with_approval after a valid token is consumed.
"""
from __future__ import annotations
from typing import Any
from auto_note import post_auto_note


def ghl_update_task(
    *,
    client,
    contact_id: str,
    task_id: str,
    reasoning: str,
    approver: str,
    title: str | None = None,
    body: str | None = None,
    due_date: str | None = None,
    completed: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    if due_date is not None:
        payload["dueDate"] = due_date
    if completed is not None:
        payload["completed"] = completed

    resp = client.put(f"/contacts/{contact_id}/tasks/{task_id}", payload=payload)
    summary_parts = []
    if title is not None:
        summary_parts.append(f"title={title}")
    if body is not None:
        summary_parts.append(f"body={body[:80]}")
    if due_date is not None:
        summary_parts.append(f"dueDate={due_date}")
    if completed is not None:
        summary_parts.append(f"completed={completed}")
    summary = "Updated task: " + ", ".join(summary_parts) if summary_parts else "Updated task: (no fields)"

    if resp.status_code in (200, 201):
        post_auto_note(
            client=client,
            contact_id=contact_id,
            action_name="ghl_update_task",
            reason=reasoning,
            approver=approver,
            result=f"success: task_id={task_id}",
            payload_summary=summary,
        )
        return {"status": "success", "task_id": task_id}
    post_auto_note(
        client=client,
        contact_id=contact_id,
        action_name="ghl_update_task",
        reason=reasoning,
        approver=approver,
        result=f"error: status={resp.status_code}",
        payload_summary=summary,
    )
    return {"status": "error", "code": resp.status_code, "body": resp.text}
