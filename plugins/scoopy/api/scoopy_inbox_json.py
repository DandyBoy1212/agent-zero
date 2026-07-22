"""GET /api/plugins/scoopy/scoopy_inbox_json
Returns pending cards as JSON for the widget."""
from __future__ import annotations
import sys, pathlib
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from approval import default_store
from scoopy_logging import log
from relay_auth import RelayAuthError, check_relay_key


class ScoopyInboxJson(ApiHandler):
    @classmethod
    def requires_auth(cls): return False
    @classmethod
    def requires_api_key(cls): return False
    @classmethod
    def requires_csrf(cls): return False
    @classmethod
    def get_methods(cls): return ["GET"]

    async def process(self, input: dict[str, Any], request) -> dict[str, Any] | Response:
        try:
            check_relay_key(request.headers.get("X-API-KEY"))
        except RelayAuthError:
            return Response(
                '{"status": "unauthorized"}',
                status=401,
                mimetype="application/json",
            )
        pending = default_store.list_pending()
        cards = []
        for token, card in pending:
            cards.append({
                "token": token,
                "contact_id": card.get("contact_id"),
                "draft": card.get("draft"),
                "reasoning": card.get("reasoning"),
                "action_type": card.get("action_type"),
                "action_count": len(card.get("pending_actions", [])),
                "skill_names": [a.get("skill") for a in card.get("pending_actions", [])],
                # The human-facing face of the card. Added to the card object
                # earlier today but not to this projection, which would have
                # shipped a card whose question was blank: the chat surface
                # renders from here and nothing else. A fixed projection
                # silently drops anything added upstream, which is exactly the
                # failure this line existed to cause.
                "summary": card.get("summary", ""),
                "detail": card.get("detail", ""),
                "customer_name": card.get("customer_name", ""),
                "trigger_context": card.get("trigger_context", "unknown"),
                "conversation_id": card.get("conversation_id", ""),
            })
        log("inbox_json_view", count=len(cards))
        return {"cards": cards}
