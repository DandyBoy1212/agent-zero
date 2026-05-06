"""ghl_list_watching_contacts — consolidate all contacts with the
`scoopy-watching` tag, optionally with each contact's open Scoopy tasks.

This is the closest thing to a 'show me all outstanding work' tool: any
contact Scoopy is currently watching (mid-conversation, mid-action) carries
the `scoopy-watching` tag, so listing them gives the operator a single
view of everything in flight.

Read-only skill. No approval gate, no auto-note.
"""
from __future__ import annotations
import os
from typing import Any

from skills_ghl_get import ghl_get_tasks_for_contact
from scoopy_logging import log


def ghl_list_watching_contacts(
    *,
    client,
    include_tasks: bool = True,
    tag: str = "scoopy-watching",
) -> list[dict[str, Any]]:
    """Return contacts tagged ``tag`` (default ``scoopy-watching``),
    optionally with each contact's open Scoopy-assigned tasks.

    Args:
        client: GhlClient instance (real or mock)
        include_tasks: if True, fetch open tasks for each contact and merge
            them onto the result. Slower (one extra API call per contact)
            but usually what the operator wants.
        tag: tag to filter by. Default is ``scoopy-watching``.

    Returns:
        list of contact dicts shaped like::
            {
                "id": "...",
                "name": "Mrs Jenkins",
                "phone": "...",
                "email": "...",
                "tags": [...],
                "tasks": [{"id": "...", "title": "[REPLY] ...", ...}],
                # "tasks_error": "..."  # only if the per-contact tasks fetch failed
            }
    """
    log("skill_helper_call", name="ghl_list_watching_contacts", tag=tag, include_tasks=include_tasks)
    # Prefer the by-tag client method if available; fall back to query-based
    # search filtered in-process.
    if hasattr(client, "search_contacts_by_tag"):
        contacts = client.search_contacts_by_tag(tag=tag) or []
    else:
        location_id = os.getenv("GHL_LOCATION_ID")
        contacts = client.search_contacts(
            query=tag, location_id=location_id, limit=100
        ) or []
        contacts = [c for c in contacts if tag in (c.get("tags") or [])]

    results: list[dict[str, Any]] = []
    for c in contacts:
        first = c.get("firstName") or ""
        last = c.get("lastName") or ""
        name = " ".join(p for p in [first, last] if p).strip()
        if not name:
            name = c.get("contactName") or "(unnamed)"

        entry: dict[str, Any] = {
            "id": c.get("id"),
            "name": name,
            "phone": c.get("phone"),
            "email": c.get("email"),
            "tags": c.get("tags", []),
        }

        if include_tasks and entry["id"]:
            try:
                entry["tasks"] = ghl_get_tasks_for_contact(
                    client=client,
                    contact_id=entry["id"],
                    assigned_to_scoopy_only=True,
                )
            except Exception as e:
                entry["tasks"] = []
                entry["tasks_error"] = str(e)

        results.append(entry)

    log("skill_helper_result", name="ghl_list_watching_contacts", status="success", count=len(results))
    return results
