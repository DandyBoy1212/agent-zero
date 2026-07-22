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
    from scoopy_chat import ScoopyChat
    from scoopy_chat_poll import ScoopyChatPoll

    return [
        ScoopyInbox,
        ScoopyInboxJson,
        ScoopySettingsGet,
        ScoopySettingsSet,
        ScoopyChat,
        ScoopyChatPoll,
    ]


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


def test_approver_comes_from_the_request(monkeypatch, key):
    """The audit trail must not attribute every approval to one person."""
    import scoopy_approve
    from scoopy_approve import ScoopyApprove

    captured = {}

    def _fake_execute(*, token, approver, client):
        captured["approver"] = approver
        return [{"status": "ok"}]

    monkeypatch.setattr(scoopy_approve, "execute_with_approval", _fake_execute)
    monkeypatch.setattr(scoopy_approve, "GhlClient", lambda: object())

    req = _Req({"X-API-KEY": key})
    req.form = {"token": "tok123", "approver": "mick.bain@scoop-patrol.co.uk"}
    _run(_build(ScoopyApprove), req)

    assert captured["approver"] == "mick.bain@scoop-patrol.co.uk"


def test_approver_defaults_to_unknown_not_to_a_name(monkeypatch, key):
    import scoopy_approve
    from scoopy_approve import ScoopyApprove

    captured = {}

    def _fake_execute(*, token, approver, client):
        captured["approver"] = approver
        return [{"status": "ok"}]

    monkeypatch.setattr(scoopy_approve, "execute_with_approval", _fake_execute)
    monkeypatch.setattr(scoopy_approve, "GhlClient", lambda: object())

    req = _Req({"X-API-KEY": key})
    req.form = {"token": "tok123"}
    _run(_build(ScoopyApprove), req)

    assert captured["approver"] == "unknown"


def test_no_relay_key_ignores_submitted_approver(monkeypatch, key):
    """The finding this closes: an unauthenticated caller must not be able
    to pin their action on someone else by simply submitting that person's
    name. Without proof the caller is the command-centre relay (which
    authenticates staff by login), the submitted `approver` must be
    discarded entirely -- not sanitized, not logged separately, just never
    forwarded -- and "unknown" recorded instead.

    This test must fail if the relay-key check is ever removed from
    scoopy_approve.process.
    """
    import scoopy_approve
    from scoopy_approve import ScoopyApprove

    captured = {}

    def _fake_execute(*, token, approver, client):
        captured["approver"] = approver
        return [{"status": "ok"}]

    monkeypatch.setattr(scoopy_approve, "execute_with_approval", _fake_execute)
    monkeypatch.setattr(scoopy_approve, "GhlClient", lambda: object())

    req = _Req()  # no X-API-KEY header at all
    req.form = {"token": "tok123", "approver": "mick.bain@scoop-patrol.co.uk"}
    result = _run(_build(ScoopyApprove), req)

    assert captured["approver"] == "unknown"
    assert "mick.bain@scoop-patrol.co.uk" not in captured.values()
    assert _status(result) == 200


def test_no_relay_key_and_no_approver_still_approves(monkeypatch, key):
    """A failed/missing relay-key check must only affect attribution, never
    whether the approval executes -- the token is still the thing being
    checked; this must never become a 401."""
    import scoopy_approve
    from scoopy_approve import ScoopyApprove

    captured = {}

    def _fake_execute(*, token, approver, client):
        captured["approver"] = approver
        return [{"status": "ok"}]

    monkeypatch.setattr(scoopy_approve, "execute_with_approval", _fake_execute)
    monkeypatch.setattr(scoopy_approve, "GhlClient", lambda: object())

    req = _Req()  # no X-API-KEY header, no approver submitted
    req.form = {"token": "tok123"}
    result = _run(_build(ScoopyApprove), req)

    assert captured["approver"] == "unknown"
    assert _status(result) == 200


def test_settings_get_agrees_with_what_is_actually_enforced(monkeypatch, key):
    """These were two copies of one rule and they had drifted: enforcement
    defaulted OFF while the settings screen defaulted ON. A UI that reports the
    opposite of reality about whether an agent can act unsupervised is the same
    class of bug as the approval widget reporting zero pending approvals while
    cards queued."""
    import skill_notify_owner as sno
    from scoopy_settings_get import ScoopySettingsGet

    monkeypatch.delenv("SCOOPY_AUTO_APPROVE", raising=False)
    monkeypatch.setattr(sno, "_RUNTIME_FILE", __import__("pathlib").Path("does-not-exist.json"))

    reported = _run(_build(ScoopySettingsGet), _Req({"X-API-KEY": key}))
    assert reported["auto_approve"] == sno._auto_approve_enabled()
    assert reported["auto_approve"] is False
