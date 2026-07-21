"""Each exposed Scoopy endpoint must refuse a request with no key.

The handlers are constructed directly rather than driven through Flask
routing, because the property under test is the in-body gate, not the
framework wiring.
"""
import asyncio
import threading

import pytest
from flask import Flask


class _Req:
    """Minimal stand-in for a Flask request; the 401 path reads only headers."""

    def __init__(self, headers=None):
        self.headers = headers or {}
        self.args = {}
        self.form = {}


def _build(handler_cls):
    return handler_cls(Flask(__name__), threading.Lock())


def _run(handler, request):
    return asyncio.run(handler.process({}, request))


def _status(result):
    """Handlers return either a Flask Response or a plain dict."""
    return getattr(result, "status_code", None)


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "test-key")
    return "test-key"


def _handlers():
    from scoopy_inbox import ScoopyInbox
    from scoopy_inbox_json import ScoopyInboxJson
    from scoopy_settings_get import ScoopySettingsGet
    from scoopy_settings_set import ScoopySettingsSet

    return [ScoopyInbox, ScoopyInboxJson, ScoopySettingsGet, ScoopySettingsSet]


@pytest.mark.parametrize("handler_cls", _handlers())
def test_no_key_is_rejected(handler_cls, key):
    result = _run(_build(handler_cls), _Req())
    assert _status(result) == 401


@pytest.mark.parametrize("handler_cls", _handlers())
def test_wrong_key_is_rejected(handler_cls, key):
    result = _run(_build(handler_cls), _Req({"X-API-KEY": "nope"}))
    assert _status(result) == 401


@pytest.mark.parametrize("handler_cls", _handlers())
def test_unconfigured_key_denies_everything(handler_cls, monkeypatch):
    monkeypatch.delenv("SCOOPY_RELAY_KEY", raising=False)
    result = _run(_build(handler_cls), _Req({"X-API-KEY": "anything"}))
    assert _status(result) == 401
