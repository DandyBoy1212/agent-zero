"""Approving must report what ran, not merely that a button was pressed.

Until 2026-07-22 this endpoint answered 200 with success styling in three
different situations: actions ran, actions failed, and there were no actions at
all. The command centre only checks res.ok, so all three drew the same green
"Approved by Liam Dand" bar.

That is not hypothetical. Liam approved a task completion, saw green, and the
task stayed open; Scoopy completed it directly through the API afterwards and
reported that the approval executor had never fired.

Handlers are constructed directly rather than driven through Flask routing,
matching test_api_auth.py: the property under test is the response the handler
decides on, not the framework wiring.
"""
import asyncio
import json
import threading
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


class _Req:
    def __init__(self, headers=None):
        self.headers = headers or {}
        self.args = {}
        self.form = {}


def _approve(results, accept="application/json"):
    """Run the handler with the dispatcher stubbed to return `results`."""
    from scoopy_approve import ScoopyApprove

    handler = ScoopyApprove(Flask(__name__), threading.Lock())
    req = _Req({"Accept": accept} if accept else {})
    with patch("scoopy_approve.execute_with_approval", return_value=results), \
         patch("scoopy_approve.GhlClient", MagicMock()):
        return asyncio.run(handler.process({"token": "tok123456"}, req))


def _json(resp):
    return json.loads(resp.get_data(as_text=True))


def test_every_action_ran():
    resp = _approve([{"status": "success"}, {"status": "success"}])
    assert resp.status_code == 200
    body = _json(resp)
    assert body["outcome"] == "executed"
    assert body["ran"] == 2
    assert body["failed"] == 0


def test_no_actions_is_not_success():
    """The empty card. Its whole summary used to be the string "no actions",
    served with success styling, which is how "nothing happened" became a
    green tick."""
    resp = _approve([])
    body = _json(resp)
    assert body["outcome"] == "nothing", "an empty card did nothing and must say so"
    assert body["ran"] == 0


def test_every_action_failed_is_not_success():
    resp = _approve([{"status": "error", "reason": "unknown skill 'ghl_complete_task'"}])
    body = _json(resp)
    assert body["outcome"] == "nothing"
    assert body["failed"] == 1
    assert "unknown skill" in body["reasons"][0]


def test_some_ran_some_failed_is_partial():
    resp = _approve([{"status": "success"}, {"status": "error", "reason": "boom"}])
    body = _json(resp)
    assert body["outcome"] == "partial"
    assert body["ran"] == 1 and body["failed"] == 1


def test_phone_path_still_gets_html():
    """The common caller is a thumb on a link in a text message, rendering this
    through HTMX. It must keep getting HTML and a 200, or a working
    confirmation becomes a broken one."""
    resp = _approve([{"status": "success"}], accept="text/html")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"
    assert "Approved" in resp.get_data(as_text=True)


def test_phone_path_is_told_when_nothing_ran():
    resp = _approve([], accept="text/html")
    text = resp.get_data(as_text=True)
    assert "nothing ran" in text
    assert 'class="card error"' in text, "a no-op must not be styled as a success"
