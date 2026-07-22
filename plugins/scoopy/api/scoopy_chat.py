"""POST /api/plugins/scoopy/scoopy_chat

The command centre relay's way in. Subclasses Agent Zero's MessageAsync so
none of the message handling, attachment saving or context management is
duplicated here; only the authentication differs.

MessageAsync accepts multipart/form-data with an `attachments` file list
(api/message.py:24-44), so file upload needs nothing added.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import Response  # noqa: E402
from api.message_async import MessageAsync  # noqa: E402
from initialize import initialize_agent  # noqa: E402

from relay_auth import RelayAuthError, check_relay_key  # noqa: E402

_UNAUTHORIZED = '{"status": "unauthorized"}'

SCOOPY_PROFILE = "scoopy"


def build_scoopy_config():
    """Agent config pinned to Scoopy's profile.

    Agent Zero's use_context() (helpers/context_utils.py:9-28) builds every
    context with a bare initialize_agent() and no profile, so a context created
    through this endpoint answers as vanilla Agent Zero, with none of Scoopy's
    prompt, tools or approval gate. Verified live 2026-07-21: the reply was
    "I'm Agent Zero, your AI assistant."
    """
    return initialize_agent(override_settings={"agent_profile": SCOOPY_PROFILE})


class ScoopyChat(MessageAsync):
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

    async def process(self, input: dict[str, Any], request) -> Any:
        try:
            check_relay_key(request.headers.get("X-API-KEY"))
        except RelayAuthError:
            return Response(_UNAUTHORIZED, status=401, mimetype="application/json")

        from agent import AgentContext

        ctxid = ""
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            ctxid = request.form.get("context", "") or ""
        elif request.is_json:
            ctxid = (request.get_json(silent=True) or {}).get("context", "") or ""

        # Create with Scoopy's profile if this thread has no context yet.
        # AgentContext.get returns None for an unknown id; the parent's
        # use_context would then build one with the default profile.
        if ctxid and AgentContext.get(ctxid) is None:
            AgentContext(config=build_scoopy_config(), id=ctxid, set_current=True)

        return await super().process(input, request)
