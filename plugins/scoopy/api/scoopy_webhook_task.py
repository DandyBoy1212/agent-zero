"""POST /api/plugins/scoopy/scoopy_webhook_task — GHL task event handler.

Triggered by GHL workflows on Task Created / Task Updated / Task Completed.
Mirrors the relevant task into Firestore so the agent has fast read access.

Filters to ONLY tasks assigned to SCOOPY_USER_ID — silently ignores any
others (no point caching unrelated tasks).
"""
from __future__ import annotations
import os
import sys
import pathlib
from typing import Any

from helpers.api import ApiHandler, Request, Response

# Plugin helpers aren't a Python package; inject the helpers dir onto sys.path
# the same way scoopy_webhook_message.py and tests/scoopy/conftest.py do.
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from webhook_dispatch import verify_signature, extract_contact_id  # noqa: E402
from webhook_task_dispatch import (  # noqa: E402
    extract_task,
    determine_event,
    build_task_doc,
)
from firestore_client import FirestoreClient  # noqa: E402


class ScoopyWebhookTask(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        raw = request.get_data() or b""
        sig = (
            request.headers.get("x-wh-signature")
            or request.headers.get("X-WH-Signature")
        )
        if not verify_signature(raw, sig):
            return Response(
                '{"status": "unauthorized"}',
                status=401,
                mimetype="application/json",
            )

        payload: dict[str, Any] = input or {}
        task = extract_task(payload)
        if not task:
            return {"status": "ignored", "reason": "no task in payload"}

        task_id = task.get("id") or payload.get("task_id") or payload.get("id")
        if not task_id:
            return {"status": "ignored", "reason": "task missing id"}
        # Make sure the task object carries the id we found
        task["id"] = task_id

        # Filter: only cache Scoopy-assigned tasks
        scoopy_id = os.getenv("SCOOPY_USER_ID")
        assigned = task.get("assignedTo") or payload.get("assignedTo")
        if scoopy_id and assigned and assigned != scoopy_id:
            return {"status": "ignored", "reason": "task not assigned to Scoopy"}

        contact_id = extract_contact_id(payload)
        contact_name = " ".join(
            filter(None, [payload.get("first_name"), payload.get("last_name")])
        ).strip() or None

        fs = FirestoreClient()

        event = determine_event(payload)
        if event["is_delete"]:
            try:
                fs.delete_task(task_id)
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"firestore delete failed: {e}",
                }
            return {"status": "deleted", "task_id": task_id}

        cache_doc = build_task_doc(
            task=task,
            payload=payload,
            contact_id=contact_id,
            contact_name=contact_name,
            fallback_assigned_to=scoopy_id,
            force_completed=event["force_completed"],
        )
        try:
            fs.upsert_task(cache_doc)
        except Exception as e:
            return {"status": "error", "reason": f"firestore upsert failed: {e}"}
        return {
            "status": "cached",
            "task_id": task_id,
            "task_type": cache_doc["task_type"],
        }
