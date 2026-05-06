"""Tests for skill_scoopy_tasks (get_tasks_for_today / get_outstanding_tasks).

We mock FirestoreClient to a recording double so we can assert that the
correct filter args are passed for each tool flavour.
"""
from datetime import date
from unittest.mock import MagicMock

import pytest

from skill_scoopy_tasks import (
    scoopy_get_tasks_for_today,
    scoopy_get_outstanding_tasks,
)
from webhook_task_dispatch import (
    parse_task_type,
    extract_task,
    is_delete_event,
    determine_event,
    build_task_doc,
)


def _fake_fs():
    """Build a MagicMock FirestoreClient that records query_tasks calls
    and returns predictable per-task-type results.
    """
    fs = MagicMock()

    def q(**kwargs):
        return [{"id": f"t-{kwargs.get('task_type','x')}", **kwargs}]

    fs.query_tasks.side_effect = q
    return fs


# --- skill_scoopy_tasks --- ----------------------------------------------


def test_get_tasks_for_today_filters_action_by_today(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    fs = _fake_fs()
    out = scoopy_get_tasks_for_today(fs=fs)
    today = date.today().isoformat()

    # Two queries: REPLY (no due filter) + ACTION (due_on_or_before=today)
    assert fs.query_tasks.call_count == 2
    calls = [c.kwargs for c in fs.query_tasks.call_args_list]
    reply_call = next(c for c in calls if c.get("task_type") == "REPLY")
    action_call = next(c for c in calls if c.get("task_type") == "ACTION")

    assert reply_call["assigned_to"] == "scoopy-id"
    assert reply_call["completed"] is False
    assert "due_on_or_before" not in reply_call

    assert action_call["assigned_to"] == "scoopy-id"
    assert action_call["completed"] is False
    assert action_call["due_on_or_before"] == today

    assert "reply" in out and "action_due" in out


def test_get_outstanding_tasks_returns_three_buckets(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    fs = _fake_fs()
    out = scoopy_get_outstanding_tasks(fs=fs)
    assert set(out.keys()) == {"reply", "action", "other"}
    # No due_date filter on any of them — broader query
    for c in fs.query_tasks.call_args_list:
        assert "due_on_or_before" not in c.kwargs
    types = sorted(c.kwargs.get("task_type") for c in fs.query_tasks.call_args_list)
    assert types == ["ACTION", "OTHER", "REPLY"]


def test_get_tasks_for_today_empty_returns_empty_lists(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    fs = MagicMock()
    fs.query_tasks.return_value = []
    out = scoopy_get_tasks_for_today(fs=fs)
    assert out == {"reply": [], "action_due": []}


def test_get_outstanding_tasks_empty_returns_empty_lists(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    fs = MagicMock()
    fs.query_tasks.return_value = []
    out = scoopy_get_outstanding_tasks(fs=fs)
    assert out == {"reply": [], "action": [], "other": []}


# --- webhook_task_dispatch helpers ---------------------------------------


def test_parse_task_type_recognises_prefixes():
    assert parse_task_type("[REPLY] hello") == "REPLY"
    assert parse_task_type("[reply] hello") == "REPLY"
    assert parse_task_type("  [ACTION] x") == "ACTION"
    assert parse_task_type("[action] x") == "ACTION"
    assert parse_task_type("regular task") == "OTHER"
    assert parse_task_type("") == "OTHER"
    assert parse_task_type(None) == "OTHER"


def test_extract_task_nested_shape():
    payload = {"task": {"id": "t1", "title": "[REPLY] x"}}
    assert extract_task(payload) == {"id": "t1", "title": "[REPLY] x"}


def test_extract_task_flat_shape():
    payload = {
        "title": "[ACTION] do thing",
        "body": "details",
        "dueDate": "2026-05-08",
        "task_id": "t9",
        "assignedTo": "scoopy-id",
    }
    out = extract_task(payload)
    assert out["id"] == "t9"
    assert out["title"] == "[ACTION] do thing"
    assert out["dueDate"] == "2026-05-08"
    assert out["assignedTo"] == "scoopy-id"


def test_extract_task_n8n_string_body():
    import json as _json
    inner = {"task": {"id": "t-inner", "title": "[REPLY] from n8n"}}
    payload = {"body": _json.dumps(inner)}
    assert extract_task(payload) == inner["task"]


def test_extract_task_returns_none_when_no_task():
    assert extract_task({"hello": "world"}) is None
    assert extract_task("not a dict") is None


def test_is_delete_event_detects_delete():
    assert is_delete_event({"event": "TaskDeleted"}) is True
    assert is_delete_event({"type": "task.delete"}) is True
    assert is_delete_event({"event": "TaskCreated"}) is False
    assert is_delete_event({}) is False


def test_build_task_doc_assembles_full_shape():
    task = {"id": "t1", "title": "[REPLY] hi", "body": "b", "dueDate": "2026-05-08"}
    payload = {"first_name": "Mrs", "last_name": "Jenkins"}
    doc = build_task_doc(
        task=task,
        payload=payload,
        contact_id="c1",
        contact_name="Mrs Jenkins",
        fallback_assigned_to="scoopy-id",
    )
    assert doc["id"] == "t1"
    assert doc["task_type"] == "REPLY"
    assert doc["due_date"] == "2026-05-08"
    assert doc["assigned_to"] == "scoopy-id"
    assert doc["contact_id"] == "c1"
    assert doc["completed"] is False


# --- determine_event + force_completed override -------------------------


def test_determine_event_completed_lowercase():
    out = determine_event({"event_type": "completed"})
    assert out == {"is_delete": False, "force_completed": True}


def test_determine_event_completed_mixed_case():
    out = determine_event({"event_type": "Completed"})
    assert out["force_completed"] is True
    assert out["is_delete"] is False


def test_determine_event_deleted_via_event_type():
    out = determine_event({"event_type": "deleted"})
    assert out == {"is_delete": True, "force_completed": None}


def test_determine_event_created_returns_no_override():
    out = determine_event({"event_type": "created"})
    assert out == {"is_delete": False, "force_completed": None}


def test_determine_event_absent_returns_no_override():
    out = determine_event({})
    assert out == {"is_delete": False, "force_completed": None}


def test_determine_event_falls_back_to_legacy_event_field():
    # Legacy payloads with `event` / `type` still detected as delete.
    assert determine_event({"event": "TaskDeleted"})["is_delete"] is True
    assert determine_event({"type": "task.delete"})["is_delete"] is True


def test_build_task_doc_force_completed_overrides_false():
    task = {"id": "t1", "title": "[REPLY] hi", "completed": False}
    doc = build_task_doc(
        task=task,
        payload={},
        contact_id="c1",
        contact_name=None,
        fallback_assigned_to="scoopy-id",
        force_completed=True,
    )
    assert doc["completed"] is True


def test_build_task_doc_force_completed_none_uses_task_field():
    task = {"id": "t1", "title": "[REPLY] hi", "completed": True}
    doc = build_task_doc(
        task=task,
        payload={},
        contact_id="c1",
        contact_name=None,
        fallback_assigned_to="scoopy-id",
        force_completed=None,
    )
    assert doc["completed"] is True
    # And without the kwarg at all (default behaviour):
    doc2 = build_task_doc(
        task={"id": "t2", "title": "x", "completed": False},
        payload={},
        contact_id=None,
        contact_name=None,
        fallback_assigned_to=None,
    )
    assert doc2["completed"] is False
