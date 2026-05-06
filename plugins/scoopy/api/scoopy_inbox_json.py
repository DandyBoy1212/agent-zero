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


class ScoopyInboxJson(ApiHandler):
    @classmethod
    def requires_auth(cls): return False
    @classmethod
    def requires_api_key(cls): return False
    @classmethod
    def requires_csrf(cls): return False
    @classmethod
    def get_methods(cls): return ["GET"]

    async def process(self, input: dict[str, Any], request) -> dict[str, Any]:
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
            })
        log("inbox_json_view", count=len(cards))
        return {"cards": cards}
