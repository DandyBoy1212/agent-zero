"""Pure-Python helpers for the scoopy_webhook_task ApiHandler.

Extracted so they're unit-testable without spinning up a Flask request
context.
"""
from __future__ import annotations
import json
from typing import Any


def parse_task_type(title: str | None) -> str:
    """Map a task title prefix to a task_type label.

    Recognised prefixes (case-insensitive, leading/trailing whitespace OK):
        [REPLY]  -> "REPLY"
        [ACTION] -> "ACTION"
    Anything else (including missing/empty title) -> "OTHER".
    """
    if not title:
        return "OTHER"
    t = title.strip().upper()
    if t.startswith("[REPLY]"):
        return "REPLY"
    if t.startswith("[ACTION]"):
        return "ACTION"
    return "OTHER"


def extract_task(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the task object from a GHL task webhook payload.

    Handles three shapes:
      1. Nested:        {"task": {"id": ..., "title": ...}, ...}
      2. Flat-KV:       {"title": ..., "body": ..., "dueDate": ..., ...}
      3. n8n wrapped:   {"body": "<json string>"} containing one of the above

    Returns None if no task object can be reconstructed.
    """
    if not isinstance(payload, dict):
        return None

    # 3. n8n wrapped string body — recurse
    body_field = payload.get("body")
    if isinstance(body_field, str):
        try:
            inner = json.loads(body_field)
            if isinstance(inner, dict):
                inner_task = extract_task(inner)
                if inner_task:
                    return inner_task
        except Exception:
            pass

    # 1. Nested under "task"
    task = payload.get("task")
    if isinstance(task, dict):
        return task

    # 2. Flat shape — title + body + dueDate at root
    if any(k in payload for k in ("title", "dueDate", "due_date")):
        return {
            "id": payload.get("task_id") or payload.get("id"),
            "title": payload.get("title"),
            "body": payload.get("body") if not isinstance(body_field, str) else "",
            "dueDate": payload.get("dueDate") or payload.get("due_date"),
            "assignedTo": payload.get("assignedTo") or payload.get("assigned_to"),
            "completed": payload.get("completed", False),
        }
    return None


def is_delete_event(payload: dict[str, Any]) -> bool:
    """Return True if the payload looks like a task-delete event."""
    if not isinstance(payload, dict):
        return False
    event = (payload.get("event") or payload.get("type") or "").lower()
    return "delete" in event or "remove" in event


def build_task_doc(
    *,
    task: dict[str, Any],
    payload: dict[str, Any],
    contact_id: str | None,
    contact_name: str | None,
    fallback_assigned_to: str | None,
) -> dict[str, Any]:
    """Build the Firestore document from a task + payload."""
    title = task.get("title", "") or ""
    assigned = (
        task.get("assignedTo")
        or payload.get("assignedTo")
        or fallback_assigned_to
    )
    return {
        "id": task.get("id"),
        "contact_id": contact_id,
        "contact_name": contact_name,
        "title": title,
        "body": task.get("body", "") or "",
        "due_date": task.get("dueDate") or task.get("due_date"),
        "completed": bool(task.get("completed", False)),
        "assigned_to": assigned,
        "task_type": parse_task_type(title),
    }
