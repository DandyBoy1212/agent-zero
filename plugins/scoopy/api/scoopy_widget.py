"""GET /api/plugins/scoopy/scoopy_widget - returns the widget JS."""
from __future__ import annotations
import pathlib
from typing import Any

from helpers.api import ApiHandler, Response

_WIDGET_JS = (pathlib.Path(__file__).resolve().parent.parent / "ui" / "scoopy_widget.js").read_text(encoding="utf-8")


class ScoopyWidget(ApiHandler):
    @classmethod
    def requires_auth(cls): return False
    @classmethod
    def requires_api_key(cls): return False
    @classmethod
    def requires_csrf(cls): return False
    @classmethod
    def get_methods(cls): return ["GET"]

    async def process(self, input: dict[str, Any], request) -> Response:
        return Response(_WIDGET_JS, status=200, mimetype="application/javascript")
