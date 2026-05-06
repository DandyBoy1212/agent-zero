"""Firestore client wrapper for Scoopy task cache.

Lazy initialization so tests can run without live creds. Production
reads creds from GOOGLE_APPLICATION_CREDENTIALS_JSON env var (a JSON
string) or service-account.json at repo root.
"""
from __future__ import annotations
import os
import json
from typing import Any
from datetime import datetime, timezone
from scoopy_logging import log, log_error, timed

_TASKS_COLLECTION = "scoopy_tasks"


def _build_client():
    """Lazy import + init. Returns None if creds unavailable."""
    try:
        from google.cloud import firestore
        from google.oauth2 import service_account
    except ImportError:
        return None
    creds = None
    json_blob = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if json_blob:
        try:
            creds = service_account.Credentials.from_service_account_info(
                json.loads(json_blob)
            )
        except Exception:
            return None
    elif os.path.exists("service-account.json"):
        try:
            creds = service_account.Credentials.from_service_account_file(
                "service-account.json"
            )
        except Exception:
            return None
    if not creds:
        return None
    try:
        return firestore.Client(credentials=creds, project=creds.project_id)
    except Exception:
        return None


class FirestoreClient:
    """Defensive Firestore wrapper for the scoopy_tasks collection.

    Tests inject a mock via ``client``. Production callers pass nothing;
    the real Firestore client is built lazily on first use.
    """

    def __init__(self, client: Any | None = None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = _build_client()
            if self._client is None:
                raise RuntimeError(
                    "Firestore client not available — missing creds "
                    "(set GOOGLE_APPLICATION_CREDENTIALS_JSON or place "
                    "service-account.json at repo root)"
                )
        return self._client

    def upsert_task(self, task: dict[str, Any]) -> None:
        task_id = task.get("id")
        if not task_id:
            raise ValueError("task missing id")
        task = dict(task)
        task["synced_at"] = datetime.now(timezone.utc).isoformat()
        self.client.collection(_TASKS_COLLECTION).document(task_id).set(task)
        log("firestore", op="upsert", collection=_TASKS_COLLECTION, doc_id=task_id, status="success")

    def delete_task(self, task_id: str) -> None:
        if not task_id:
            raise ValueError("task_id required")
        self.client.collection(_TASKS_COLLECTION).document(task_id).delete()
        log("firestore", op="delete", collection=_TASKS_COLLECTION, doc_id=task_id, status="success")

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        doc = self.client.collection(_TASKS_COLLECTION).document(task_id).get()
        exists = getattr(doc, "exists", False)
        log("firestore", op="get", collection=_TASKS_COLLECTION, doc_id=task_id, status="success", found=bool(exists))
        if not exists:
            return None
        return doc.to_dict()

    def query_tasks(
        self,
        *,
        assigned_to: str | None = None,
        completed: bool | None = None,
        due_on_or_before: str | None = None,
        task_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with timed("firestore", op="query", collection=_TASKS_COLLECTION) as ctx:
            q = self.client.collection(_TASKS_COLLECTION)
            filters = []
            if assigned_to is not None:
                q = q.where("assigned_to", "==", assigned_to)
                filters.append("assigned_to")
            if completed is not None:
                q = q.where("completed", "==", completed)
                filters.append("completed")
            if task_type is not None:
                q = q.where("task_type", "==", task_type)
                filters.append("task_type")
            if due_on_or_before is not None:
                q = q.where("due_date", "<=", due_on_or_before)
                filters.append("due_date")
            docs = q.limit(limit).stream()
            results = [d.to_dict() for d in docs]
            ctx["filters"] = ",".join(filters)
            ctx["result_count"] = len(results)
            ctx["status"] = "success"
        return results
