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

_RUNTIME_FILE = pathlib.Path("tmp/scoopy_runtime.json")


class ScoopySettingsGet(ApiHandler):
    @classmethod
    def requires_auth(cls): return False
    @classmethod
    def requires_api_key(cls): return False
    @classmethod
    def requires_csrf(cls): return False
    @classmethod
    def get_methods(cls): return ["GET"]

    async def process(self, input: dict[str, Any], request) -> dict[str, Any]:
        auto_approve = None
        try:
            if _RUNTIME_FILE.exists():
                data = json.loads(_RUNTIME_FILE.read_text(encoding="utf-8"))
                if "auto_approve" in data:
                    auto_approve = bool(data["auto_approve"])
        except Exception:
            pass
        if auto_approve is None:
            env_val = os.getenv("SCOOPY_AUTO_APPROVE", "1").strip()
            auto_approve = env_val not in ("", "0", "false", "False", "no", "NO")
        log("settings_get", auto_approve=auto_approve)
        return {"auto_approve": auto_approve}
