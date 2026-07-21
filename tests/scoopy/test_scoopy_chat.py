import asyncio
import threading

import pytest
from flask import Flask


class _Req:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.args = {}
        self.form = {}
        self.content_type = "application/json"


def _build(handler_cls):
    return handler_cls(Flask(__name__), threading.Lock())


def _run(handler, request):
    return asyncio.run(handler.process({}, request))


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "test-key")
    return "test-key"


def test_chat_rejects_a_request_with_no_key(key):
    from scoopy_chat import ScoopyChat

    result = _run(_build(ScoopyChat), _Req())
    assert result.status_code == 401


def test_chat_poll_rejects_a_request_with_no_key(key):
    from scoopy_chat_poll import ScoopyChatPoll

    result = _run(_build(ScoopyChatPoll), _Req())
    assert result.status_code == 401


def test_chat_rejects_a_wrong_key(key):
    from scoopy_chat import ScoopyChat

    result = _run(_build(ScoopyChat), _Req({"X-API-KEY": "nope"}))
    assert result.status_code == 401


def test_chat_does_not_reintroduce_the_open_endpoint_pattern():
    """The framework flags stay False because the gate reads the
    environment rather than settings.json, which is wiped on restart. The
    protection must therefore be in the body. This test exists so nobody
    later 'tidies up' by deleting the in-body check."""
    import inspect

    from scoopy_chat import ScoopyChat

    source = inspect.getsource(ScoopyChat)
    assert "check_relay_key" in source
