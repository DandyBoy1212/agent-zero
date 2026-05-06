"""Auto-note helper. Every write skill calls this as a side effect.

The note format is the canonical Scoopy audit trail entry — appears on the
contact in GHL native UI for every action Scoopy takes.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def format_note(
    *,
    action_name: str,
    reason: str,
    approver: str,
    result: str,
    timestamp: str | None = None,
    payload_summary: str | None = None,
) -> str:
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    body = (
        f"[Scoopy] {action_name}\n"
        f"When: {ts}\n"
        f"Reason: {reason}\n"
        f"Approved by: {approver}\n"
        f"Result: {result}"
    )
    if payload_summary:
        body += f"\n{payload_summary}"
    return body


def post_auto_note(
    *,
    client: Any,
    contact_id: str,
    action_name: str,
    reason: str,
    approver: str,
    result: str,
    payload_summary: str | None = None,
) -> bool:
    body = format_note(
        action_name=action_name,
        reason=reason,
        approver=approver,
        result=result,
        payload_summary=payload_summary,
    )
    resp = client.post(f"/contacts/{contact_id}/notes", payload={"body": body})
    return resp.status_code in (200, 201)
