"""One-shot backfill: pull existing scoopy-watching contacts' tasks from
GHL into Firestore. Run after first deploy or whenever the cache drifts
from the source of truth (GHL).

Usage from a Python REPL or one-off script:

    import sys
    sys.path.insert(0, "plugins/scoopy/helpers")
    from scoopy_backfill_tasks import backfill
    print(backfill())
"""
from __future__ import annotations
import os
from typing import Any

from ghl_client import GhlClient
from firestore_client import FirestoreClient
from skill_ghl_list_watching import ghl_list_watching_contacts
from webhook_task_dispatch import parse_task_type


def backfill(
    *,
    ghl: GhlClient | None = None,
    fs: FirestoreClient | None = None,
) -> dict[str, int]:
    """Walk all scoopy-watching contacts, pull their open tasks, and seed
    Firestore. Returns a small summary dict.
    """
    ghl = ghl or GhlClient()
    fs = fs or FirestoreClient()
    scoopy_id = os.getenv("SCOOPY_USER_ID")

    contacts = ghl_list_watching_contacts(client=ghl, include_tasks=True)
    cached = 0
    for c in contacts:
        for t in c.get("tasks", []) or []:
            tid = t.get("id")
            if not tid:
                continue
            title = t.get("title", "") or ""
            doc: dict[str, Any] = {
                "id": tid,
                "contact_id": c.get("id"),
                "contact_name": c.get("name"),
                "title": title,
                "body": t.get("body", "") or "",
                "due_date": t.get("dueDate"),
                "completed": bool(t.get("completed", False)),
                "assigned_to": t.get("assignedTo") or scoopy_id,
                "task_type": parse_task_type(title),
            }
            try:
                fs.upsert_task(doc)
                cached += 1
            except Exception:
                # Best-effort: keep going on per-task failures
                continue
    return {"contacts_processed": len(contacts), "tasks_cached": cached}
