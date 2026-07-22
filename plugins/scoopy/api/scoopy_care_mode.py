"""GET/POST /api/plugins/scoopy/scoopy_care_mode

Reads or sets max mode for one conversation, so the command centre can offer a
person the same step-up Scoopy can give himself.

A person's choice is thread-scoped: it stays on until they turn it off. Scoopy's
own is turn-scoped and clears itself. See plugins/scoopy/helpers/care_mode.py
for why those differ.

Key-gated both ways. This one costs money per turn, so it is not something an
unauthenticated caller gets to switch on and walk away from.
"""
from __future__ import annotations
import pathlib
import sys
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from agent import AgentContext
from care_mode import current_mode, engage, release
from relay_auth import RelayAuthError, check_relay_key
from scoopy_logging import log

_UNAUTHORIZED = '{"status": "unauthorized"}'


class ScoopyCareMode(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool: return False
    @classmethod
    def requires_api_key(cls) -> bool: return False
    @classmethod
    def requires_csrf(cls) -> bool: return False
    @classmethod
    def get_methods(cls) -> list[str]: return ["GET", "POST"]

    async def process(self, input: dict[str, Any], request) -> Any:
        try:
            check_relay_key(request.headers.get("X-API-KEY"))
        except RelayAuthError:
            return Response(_UNAUTHORIZED, status=401, mimetype="application/json")

        body = input or {}
        ctxid = str(body.get("context") or request.args.get("context") or "").strip()
        if not ctxid:
            return {"status": "error", "reason": "context is required"}

        # Deliberately does NOT create one. An unknown id here means the caller
        # is asking about a conversation that does not exist, and inventing an
        # empty one to answer would report "everyday" about nothing.
        context = AgentContext.get(ctxid)
        if context is None:
            return {"status": "error", "reason": "unknown conversation"}

        if request.method == "GET":
            return {"status": "ok", "mode": current_mode(context)}

        if "max" not in body:
            return {"status": "error", "reason": "max missing"}

        if bool(body["max"]):
            engage(context, scope="thread", reason="set by a person in the command centre")
        else:
            # Clears a turn-scoped escalation too. Someone switching this off is
            # saying "stop spending", and honouring only half of that would be
            # a strange reading of it.
            release(context)

        mode = current_mode(context)
        log("care_mode_set", mode=mode, by="relay")
        return {"status": "ok", "mode": mode}
