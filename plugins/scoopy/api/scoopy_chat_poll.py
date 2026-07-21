"""POST /api/plugins/scoopy/scoopy_chat_poll

Same relationship to Agent Zero's Poll handler as scoopy_chat has to
MessageAsync: identical behaviour, different authentication. The relay
polls this for replies after posting a message.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import Response  # noqa: E402
from api.poll import Poll  # noqa: E402

from relay_auth import RelayAuthError, check_relay_key  # noqa: E402

_UNAUTHORIZED = '{"status": "unauthorized"}'


class ScoopyChatPoll(Poll):
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
        return await super().process(input, request)
