"""Scoopy GHL inbound-message webhook handler.

Endpoint: POST /api/plugins/scoopy/scoopy_webhook_message

Triggered by GHL when a customer replies. We:
  1. Verify webhook signature
  2. Find any open [REPLY] tasks assigned to Scoopy on the contact
  3. If matched, wake Master Scoopy with a synthetic prompt; return async
"""
from __future__ import annotations
import sys
import pathlib
import uuid
from typing import Any

from agent import AgentContext, UserMessage, AgentContextType
from helpers.api import ApiHandler, Request, Response
from initialize import initialize_agent

# Plugin helpers aren't a Python package; inject the helpers dir onto sys.path
# the same way tests/scoopy/conftest.py does.
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from webhook_dispatch import (  # noqa: E402
    verify_signature,
    extract_contact_id,
    find_matching_reply_tasks,
    build_synthetic_prompt,
    extract_message,
)
from ghl_client import GhlClient  # noqa: E402


class ScoopyWebhookMessage(ApiHandler):
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
            request.headers.get("x-ghl-signature")
            or request.headers.get("X-GHL-Signature")
        )
        if not verify_signature(raw, sig):
            return Response(
                '{"status": "unauthorized"}',
                status=401,
                mimetype="application/json",
            )

        payload: dict[str, Any] = input or {}
        contact_id = extract_contact_id(payload)
        if not contact_id:
            return Response(
                '{"status": "bad_request", "reason": "missing contact_id"}',
                status=400,
                mimetype="application/json",
            )

        client = GhlClient()
        tasks = find_matching_reply_tasks(client=client, contact_id=contact_id)
        if not tasks:
            return {
                "status": "ignored",
                "reason": "no [REPLY] task assigned to Scoopy",
            }

        # Best-effort contact fetch for prompt enrichment
        try:
            contact = client.get_contact(contact_id)
        except Exception:
            contact = None

        message = extract_message(payload)
        prompt = build_synthetic_prompt(
            contact_id=contact_id,
            tasks=tasks,
            message=message,
            contact=contact,
        )

        # Build agent context — mirror api/api_message.py conventions
        config = initialize_agent()
        context = AgentContext(config=config, type=AgentContextType.USER)
        AgentContext.use(context.id)

        # Fire-and-forget: don't await the result (async handling)
        msg_id = str(uuid.uuid4())
        context.communicate(
            UserMessage(message=prompt, attachments=[], id=msg_id)
        )

        return {
            "status": "accepted",
            "context_id": context.id,
            "tasks_matched": len(tasks),
        }
