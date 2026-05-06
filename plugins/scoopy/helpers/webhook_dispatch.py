"""Webhook dispatch helpers.

Pure-Python module so dispatch logic is unit-testable. The ApiHandler in
plugins/scoopy/api/scoopy_webhook_message.py imports from here.
"""
from __future__ import annotations
import os
import hmac
import hashlib
import json
from typing import Any
from ghl_client import GhlClient
from skills_ghl_get import ghl_get_tasks_for_contact


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify GHL webhook signature.

    Test-mode bypass: WEBHOOK_TEST_MODE=1 always returns True.

    Real verification: HMAC-SHA256 of raw body using GHL_WEBHOOK_SECRET.
    NOTE: GHL's actual signature header name + algorithm should be
    confirmed against GHL docs in production. This is a defensible default.
    """
    if os.getenv("WEBHOOK_TEST_MODE") == "1":
        return True
    secret = os.getenv("GHL_WEBHOOK_SECRET", "")
    if not secret or not signature_header:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def extract_contact_id(payload: dict[str, Any]) -> str | None:
    """GHL webhooks come in a few shapes. Handle the common ones."""
    # Common direct fields:
    cid = payload.get("contact_id") or payload.get("contactId")
    if cid:
        return cid
    # Nested under "contact":
    contact = payload.get("contact")
    if isinstance(contact, dict):
        return contact.get("id")
    # n8n-wrapped: body is a JSON string
    body = payload.get("body")
    if isinstance(body, str):
        try:
            inner = json.loads(body)
            return extract_contact_id(inner)
        except Exception:
            pass
    elif isinstance(body, dict):
        return extract_contact_id(body)
    return None


def find_matching_reply_tasks(
    *,
    client: GhlClient,
    contact_id: str,
) -> list[dict[str, Any]]:
    """Return the contact's open [REPLY] tasks assigned to Scoopy."""
    return ghl_get_tasks_for_contact(
        client=client,
        contact_id=contact_id,
        assigned_to_scoopy_only=True,
        title_prefix="[REPLY]",
    )


def build_synthetic_prompt(
    *,
    contact_id: str,
    tasks: list[dict[str, Any]],
    message: dict[str, Any],
    contact: dict[str, Any] | None = None,
) -> str:
    """Build the prompt sent into Master Scoopy when a webhook fires.

    The prompt frames the situation: which contact, which task, what they said.
    """
    task_block = "\n".join(
        f"- Task {t.get('id')}: {t.get('title')}\n  Body: {t.get('body','(none)')}"
        for t in tasks
    )
    message_body = (message or {}).get("body") or (message or {}).get("message") or "(no body)"
    contact_name = ""
    if contact:
        c = contact.get("contact") or contact
        contact_name = f" {c.get('firstName','')} {c.get('lastName','')}".strip()
    return (
        f"Customer{(' ' + contact_name) if contact_name else ''} (contact_id={contact_id}) "
        f"replied to a Scoop Patrol conversation.\n\n"
        f"Their message:\n> {message_body}\n\n"
        f"Active [REPLY] task(s) assigned to you for this contact:\n"
        f"{task_block}\n\n"
        f"Read business_context.md, search Mem0 for relevant context, "
        f"reason about whether this reply is in-scope of the task, and either "
        f"draft a reply (in-scope) or a holding response (drift) by calling "
        f"notify_owner. Do NOT call any write skill directly."
    )
