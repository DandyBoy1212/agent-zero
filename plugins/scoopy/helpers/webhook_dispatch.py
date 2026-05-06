"""Webhook dispatch helpers.

Pure-Python module so dispatch logic is unit-testable. The ApiHandler in
plugins/scoopy/api/scoopy_webhook_message.py imports from here.
"""
from __future__ import annotations
import os
import json
import base64
from typing import Any
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from ghl_client import GhlClient
from skills_ghl_get import ghl_get_tasks_for_contact


# GHL global webhook public key. Source:
# highlevel-api-docs/docs/oauth/WebhookAuthentication.md (lines 41-54).
# This is the SAME key for every GHL location/integration. GHL rotates
# rarely; watch the developer Slack channel for notice.
GHL_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAokvo/r9tVgcfZ5DysOSC
Frm602qYV0MaAiNnX9O8KxMbiyRKWeL9JpCpVpt4XHIcBOK4u3cLSqJGOLaPuXw6
dO0t6Q/ZVdAV5Phz+ZtzPL16iCGeK9po6D6JHBpbi989mmzMryUnQJezlYJ3DVfB
csedpinheNnyYeFXolrJvcsjDtfAeRx5ByHQmTnSdFUzuAnC9/GepgLT9SM4nCpv
uxmZMxrJt5Rw+VUaQ9B8JSvbMPpez4peKaJPZHBbU3OdeCVx5klVXXZQGNHOs8gF
3kvoV5rTnXV0IknLBXlcKKAQLZcY/Q9rG6Ifi9c+5vqlvHPCUJFT5XUGG5RKgOKU
J062fRtN+rLYZUV+BjafxQauvC8wSWeYja63VSUruvmNj8xkx2zE/Juc+yjLjTXp
IocmaiFeAO6fUtNjDeFVkhf5LNb59vECyrHD2SQIrhgXpO4Q3dVNA5rw576PwTzN
h/AMfHKIjE4xQA1SZuYJmNnmVZLIZBlQAF9Ntd03rfadZ+yDiOXCCs9FkHibELhC
HULgCsnuDJHcrGNd5/Ddm5hxGQ0ASitgHeMZ0kcIOwKDOzOU53lDza6/Y09T7sYJ
PQe7z0cvj7aE4B+Ax1ZoZGPzpJlZtGXCsu9aTEGEnKzmsFqwcSsnw3JB31IGKAyk
T1hhTiaCeIY/OwwwNUY2yvcCAwEAAQ==
-----END PUBLIC KEY-----"""


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify a GHL webhook signature.

    GHL signs the raw request body with RSA-SHA256 using a global private
    key; we verify with the public key shipped above. Header name is
    ``x-wh-signature`` and the value is base64-encoded.

    Test-mode bypass: when ``WEBHOOK_TEST_MODE=1`` the function always
    returns True so local/dev runs and the test suite don't need a real
    signature.
    """
    if os.getenv("WEBHOOK_TEST_MODE") == "1":
        return True
    if not signature_header:
        return False
    try:
        key = serialization.load_pem_public_key(GHL_PUBLIC_KEY_PEM)
        sig_bytes = base64.b64decode(signature_header)
        key.verify(sig_bytes, raw_body, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def extract_contact_id(payload: dict[str, Any]) -> str | None:
    """GHL inbound webhooks deliver a FLAT payload — `contactId` lives at
    the top level (camelCase), per
    highlevel-api-docs/docs/webhook events/InboundMessage.md (lines 22-76).
    We still tolerate the legacy snake_case name and the n8n-wrapped
    `body` shape so retro fixtures keep working.
    """
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
