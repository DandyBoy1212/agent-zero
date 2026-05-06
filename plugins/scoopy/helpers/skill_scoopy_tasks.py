"""scoopy_get_tasks_for_today / scoopy_get_outstanding_tasks helpers.

Reads from Firestore cache populated by the task webhook handler
(plugins/scoopy/api/scoopy_webhook_task.py).
"""
from __future__ import annotations
import os
from datetime import date
from typing import Any

from firestore_client import FirestoreClient
from scoopy_logging import log


def scoopy_get_tasks_for_today(
    *, fs: FirestoreClient | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Return tasks Scoopy should work on today, split by type.

    Includes:
    - [REPLY] tasks (waiting on customer reply — listed for visibility,
      not direct action; the inbound-message webhook will wake the agent
      when a reply actually arrives)
    - [ACTION] tasks due on or before today

    Returns: {"reply": [...], "action_due": [...]}
    """
    log("skill_helper_call", name="scoopy_get_tasks_for_today")
    fs = fs or FirestoreClient()
    scoopy_id = os.getenv("SCOOPY_USER_ID")
    today_iso = date.today().isoformat()

    reply = fs.query_tasks(
        assigned_to=scoopy_id, completed=False, task_type="REPLY",
    )
    action_due = fs.query_tasks(
        assigned_to=scoopy_id,
        completed=False,
        task_type="ACTION",
        due_on_or_before=today_iso,
    )
    log(
        "skill_helper_result",
        name="scoopy_get_tasks_for_today",
        status="success",
        reply_count=len(reply),
        action_due_count=len(action_due),
    )
    return {"reply": reply, "action_due": action_due}


def scoopy_get_outstanding_tasks(
    *, fs: FirestoreClient | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Return ALL outstanding tasks assigned to Scoopy, regardless of due date.

    Use when the operator asks "what's outstanding" / "show me everything
    Scoopy is watching."
    """
    log("skill_helper_call", name="scoopy_get_outstanding_tasks")
    fs = fs or FirestoreClient()
    scoopy_id = os.getenv("SCOOPY_USER_ID")

    reply = fs.query_tasks(
        assigned_to=scoopy_id, completed=False, task_type="REPLY"
    )
    action = fs.query_tasks(
        assigned_to=scoopy_id, completed=False, task_type="ACTION"
    )
    other = fs.query_tasks(
        assigned_to=scoopy_id, completed=False, task_type="OTHER"
    )
    log(
        "skill_helper_result",
        name="scoopy_get_outstanding_tasks",
        status="success",
        reply_count=len(reply),
        action_count=len(action),
        other_count=len(other),
    )
    return {"reply": reply, "action": action, "other": other}
