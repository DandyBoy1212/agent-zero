"""GET /api/plugins/scoopy/scoopy_inbox

Renders the inbox page (or, with ?fragment=1, just the cards fragment for HTMX polling).
"""
from __future__ import annotations
import sys, pathlib
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from approval import default_store
from inbox_render import render_inbox
from scoopy_logging import log

_TEMPLATE = (pathlib.Path(__file__).resolve().parent.parent / "ui" / "inbox.html").read_text(encoding="utf-8")


class ScoopyInbox(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool: return False
    @classmethod
    def requires_api_key(cls) -> bool: return False
    @classmethod
    def requires_csrf(cls) -> bool: return False
    @classmethod
    def get_methods(cls) -> list[str]: return ["GET"]

    async def process(self, input: dict[str, Any], request) -> Response:
        pending = default_store.list_pending()
        log("inbox_view", pending_count=len(pending))
        cards_html = render_inbox(pending)
        # ?fragment=1 -> return just the cards (for HTMX polling refresh)
        if request.args.get("fragment") == "1":
            return Response(cards_html, status=200, mimetype="text/html")
        body = _TEMPLATE.replace("{{CARDS}}", cards_html)
        return Response(body, status=200, mimetype="text/html")
