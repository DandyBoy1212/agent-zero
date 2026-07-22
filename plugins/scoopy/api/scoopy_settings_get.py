"""GET /api/plugins/scoopy/scoopy_settings_get
Returns current auto_approve state (runtime file > env var > default true)."""
from __future__ import annotations
import os, sys, pathlib
import json
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from scoopy_logging import log
from relay_auth import RelayAuthError, check_relay_key
from skill_notify_owner import _auto_approve_enabled

_RUNTIME_FILE = pathlib.Path("usr/scoopy_runtime.json")


class ScoopySettingsGet(ApiHandler):
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
        # Ask the same function that ENFORCES it, rather than reimplementing
        # the rule. These had drifted: enforcement defaulted to off while this
        # copy still defaulted to on, so the settings screen would have told
        # staff that Scoopy was acting freely when he was asking for
        # everything. A second copy of a rule is a second answer waiting to
        # happen, and this surface exists to tell a human the truth about
        # whether the agent can act unsupervised.
        auto_approve = _auto_approve_enabled()
        log("settings_get", auto_approve=auto_approve)
        return {"auto_approve": auto_approve}
