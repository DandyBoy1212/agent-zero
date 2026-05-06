"""POST /api/plugins/scoopy/scoopy_approve

Consumes the approval token, runs queued skills via the dispatcher,
returns an HTML confirmation snippet (HTMX-friendly).
"""
from __future__ import annotations
import sys, pathlib
from html import escape
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from approval import ApprovalError
from dispatcher import execute_with_approval
from ghl_client import GhlClient


class ScoopyApprove(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool: return False
    @classmethod
    def requires_api_key(cls) -> bool: return False
    @classmethod
    def requires_csrf(cls) -> bool: return False
    @classmethod
    def get_methods(cls) -> list[str]: return ["POST"]

    async def process(self, input: dict[str, Any], request) -> Response:
        token = (input or {}).get("token") or request.form.get("token") or request.args.get("token")
        if not token:
            return Response('<div class="card error">missing token</div>', status=400, mimetype="text/html")
        try:
            client = GhlClient()
            results = execute_with_approval(token=token, approver="liam", client=client)
        except ApprovalError as e:
            return Response(f'<div class="card error">approval error: {escape(str(e))}</div>', status=400, mimetype="text/html")
        # Summary HTML
        summary = " &middot; ".join(escape(r.get("status","?")) for r in results) or "no actions"
        html = f'<div class="card success">Approved &rarr; {summary}</div>'
        return Response(html, status=200, mimetype="text/html")
