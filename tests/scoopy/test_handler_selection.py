"""A file's own handler class must win over one it imported.

This is the bug that stopped voice notes working in production. The route
`/api/plugins/scoopy/scoopy_transcribe` dispatched to Agent Zero's stock
`Transcribe` rather than to `ScoopyTranscribe`, so it demanded a CSRF token
that a server-to-server call cannot have and answered 403 with "CSRF token
missing or invalid", regardless of the subclass declaring requires_csrf False.

The cause was name ordering, not inheritance. `load_classes_from_file` sorted
members alphabetically, walked the list backwards and took the first match, so
a subclass only won when its name happened to sort after its parent's.
ScoopyChat beat MessageAsync and ScoopyChatPoll beat Poll, which is why this
went unnoticed. ScoopyTranscribe lost to Transcribe.

These tests use the real loader against real files, because the failure was
entirely about which class the loader picks and a hand-built fake would prove
nothing about it.
"""
import pathlib

import pytest

from helpers.api import ApiHandler
from helpers.modules import load_classes_from_file

_API = pathlib.Path(__file__).resolve().parents[2] / "plugins" / "scoopy" / "api"


def _picked(filename: str):
    classes = load_classes_from_file(str(_API / filename), ApiHandler)
    assert classes, f"{filename} yielded no handler at all"
    return classes[0]


def test_transcribe_picks_the_scoopy_subclass_not_the_stock_handler():
    """The regression itself. Fails on the old loader."""
    assert _picked("scoopy_transcribe.py").__name__ == "ScoopyTranscribe"


def test_transcribe_handler_is_not_csrf_gated():
    """What the wrong class actually cost: a 403 on every voice note."""
    cls = _picked("scoopy_transcribe.py")
    assert cls.requires_csrf() is False
    assert cls.requires_auth() is False


@pytest.mark.parametrize(
    "filename,expected",
    [
        # These two already worked, purely because of how their names sort.
        # They are here so the fix cannot regress them while fixing the third.
        ("scoopy_chat.py", "ScoopyChat"),
        ("scoopy_chat_poll.py", "ScoopyChatPoll"),
        ("scoopy_transcribe.py", "ScoopyTranscribe"),
    ],
)
def test_every_subclassing_handler_resolves_to_its_own_class(filename, expected):
    assert _picked(filename).__name__ == expected


def test_handlers_that_import_no_parent_are_unaffected():
    for filename in ("scoopy_approve.py", "scoopy_inbox_json.py", "scoopy_care_mode.py"):
        cls = _picked(filename)
        assert cls.__module__.endswith(filename[:-3]), (
            f"{filename} resolved to {cls.__name__} from {cls.__module__}"
        )
