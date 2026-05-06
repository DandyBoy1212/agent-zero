"""POST /api/plugins/scoopy/scoopy_settings_set  body: {"auto_approve": bool}
Writes the runtime settings file."""
from __future__ import annotations
import sys, pathlib, json
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from scoopy_logging import log, log_error

_RUNTIME_FILE = pathlib.Path("tmp/scoopy_runtime.json")


class ScoopySettingsSet(ApiHandler):
    @classmethod
    def requires_auth(cls): return False
    @classmethod
    def requires_api_key(cls): return False
    @classmethod
    def requires_csrf(cls): return False
    @classmethod
    def get_methods(cls): return ["POST"]

    async def process(self, input: dict[str, Any], request) -> dict[str, Any]:
        body = input or {}
        if "auto_approve" not in body:
            return {"status": "error", "reason": "auto_approve missing"}
        new_val = bool(body["auto_approve"])
        try:
            _RUNTIME_FILE.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if _RUNTIME_FILE.exists():
                try:
                    existing = json.loads(_RUNTIME_FILE.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}
            existing["auto_approve"] = new_val
            _RUNTIME_FILE.write_text(json.dumps(existing), encoding="utf-8")
            log("settings_set", auto_approve=new_val)
            return {"status": "ok", "auto_approve": new_val}
        except Exception as e:
            log_error("settings_set_failed", exc=e)
            return {"status": "error", "reason": str(e)}
