"""POST /api/plugins/scoopy/scoopy_reject

Discards the approval token without running any action.
Returns an HTML confirmation snippet.
"""
from __future__ import annotations
import sys, pathlib
from html import escape
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from approval import default_store, ApprovalError
from scoopy_logging import log


class ScoopyReject(ApiHandler):
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
            log("reject_clicked", token_prefix=None)
            return Response('<div class="card error">missing token</div>', status=400, mimetype="text/html")
        log("reject_clicked", token_prefix=token[:6] if isinstance(token, str) else None)
        try:
            default_store.consume(token)
        except ApprovalError as e:
            log("approval_rejected", token_prefix=token[:6], reason=str(e))
            return Response(f'<div class="card error">{escape(str(e))}</div>', status=400, mimetype="text/html")
        log("reject_complete", token_prefix=token[:6])
        return Response('<div class="card rejected">Rejected.</div>', status=200, mimetype="text/html")
