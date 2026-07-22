"""POST /api/plugins/scoopy/scoopy_transcribe

Same relationship to Agent Zero's Transcribe handler as scoopy_chat has to
MessageAsync: identical behaviour, different authentication.

Why this exists. The command centre relay records a voice note in the browser
and posts the audio server-side for transcription. Agent Zero's own
`/api/transcribe` is a plain ApiHandler, so it inherits session auth plus CSRF
and answers a server-to-server call with 403. Verified against production
2026-07-22:

    $ curl -X POST https://agent-zero-1-h0f7.onrender.com/api/transcribe
    403

Without this endpoint the voice button would fail in production while working
in any browser that happened to be logged in, which is the most annoying class
of bug to chase.

Note on cost, recorded here because it decides a later choice. This runs
Whisper locally on Scoopy's own box: `helpers/whisper.py:41` loads the model
from /tmp/models/whisper, which Render does NOT persist (one disk per service,
and ours is mounted at /a0/usr), so the model re-downloads on every restart and
the first voice note after a deploy waits for it. Transcribing also competes
for the same CPU that is running the agent. The relay keeps a swappable
`SCOOPY_TRANSCRIBE_MODE` for exactly this reason. Measure before choosing.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import Response  # noqa: E402
from api.transcribe import Transcribe  # noqa: E402

from relay_auth import RelayAuthError, check_relay_key  # noqa: E402

_UNAUTHORIZED = '{"status": "unauthorized"}'


class ScoopyTranscribe(Transcribe):
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
