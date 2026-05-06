"""Read-only GHL skills.

Used by the webhook handler to fetch context before waking the agent. No
approval gate, no auto-note (reads aren't actions). Each function takes a
GhlClient as a parameter so it can be swapped/mocked.
"""
from __future__ import annotations
import os
from typing import Any
from scoopy_logging import log


def ghl_get_contact(*, client, contact_id: str) -> dict[str, Any]:
    """Return GHL contact payload (custom fields, tags, basic info)."""
    log("skill_helper_call", name="ghl_get_contact", contact_id=contact_id)
    result = client.get_contact(contact_id)
    log("skill_helper_result", name="ghl_get_contact", status="success")
    return result


def ghl_get_tasks_for_contact(
    *,
    client,
    contact_id: str,
    assigned_to_scoopy_only: bool = False,
    title_prefix: str | None = None,
) -> list[dict[str, Any]]:
    """Return open tasks for the contact, optionally filtered.

    Args:
        client: GhlClient
        contact_id: GHL contact id
        assigned_to_scoopy_only: if True, return only tasks where assignedTo
            matches env var SCOOPY_USER_ID
        title_prefix: if set, return only tasks whose title startswith this
            prefix (e.g. "[REPLY]" or "[ACTION]")
    """
    log(
        "skill_helper_call",
        name="ghl_get_tasks_for_contact",
        contact_id=contact_id,
        assigned_to_scoopy_only=assigned_to_scoopy_only,
        title_prefix=title_prefix,
    )
    tasks = client.get_tasks_for_contact(contact_id)
    # Always exclude completed
    tasks = [t for t in tasks if not t.get("completed", False)]
    if assigned_to_scoopy_only:
        scoopy_id = os.getenv("SCOOPY_USER_ID")
        tasks = [t for t in tasks if t.get("assignedTo") == scoopy_id]
    if title_prefix:
        tasks = [t for t in tasks if t.get("title", "").startswith(title_prefix)]
    log("skill_helper_result", name="ghl_get_tasks_for_contact", status="success", count=len(tasks))
    return tasks


def ghl_get_conversation(*, client, conversation_id: str) -> dict[str, Any]:
    """Return conversation messages payload."""
    log("skill_helper_call", name="ghl_get_conversation", conversation_id=conversation_id)
    result = client.get_conversation(conversation_id)
    log("skill_helper_result", name="ghl_get_conversation", status="success")
    return result
