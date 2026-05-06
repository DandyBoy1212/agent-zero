"""Tests for the FirestoreClient wrapper.

We never spin up the real google-cloud-firestore client — every test
injects a recording mock so we can assert on the call chain.
"""
from unittest.mock import MagicMock

import pytest

import firestore_client as fc_mod
from firestore_client import FirestoreClient


def _make_recording_mock():
    """Build a mock that records `.collection(...).document(...).set(...)`
    and `.where(...).where(...).limit(...).stream()` chains.
    """
    mock = MagicMock()
    return mock


def test_upsert_writes_to_collection_and_sets_synced_at():
    mock = _make_recording_mock()
    fc = FirestoreClient(client=mock)
    fc.upsert_task({"id": "t1", "title": "[REPLY] hello", "completed": False})

    # Should call .collection("scoopy_tasks").document("t1").set(<dict>)
    mock.collection.assert_called_once_with("scoopy_tasks")
    coll = mock.collection.return_value
    coll.document.assert_called_once_with("t1")
    doc = coll.document.return_value
    assert doc.set.call_count == 1
    written = doc.set.call_args[0][0]
    assert written["id"] == "t1"
    assert written["title"] == "[REPLY] hello"
    assert "synced_at" in written and written["synced_at"]  # ISO string


def test_upsert_raises_without_id():
    fc = FirestoreClient(client=MagicMock())
    with pytest.raises(ValueError):
        fc.upsert_task({"title": "no id"})


def test_delete_calls_document_delete():
    mock = MagicMock()
    fc = FirestoreClient(client=mock)
    fc.delete_task("t1")
    mock.collection.assert_called_once_with("scoopy_tasks")
    mock.collection.return_value.document.assert_called_once_with("t1")
    mock.collection.return_value.document.return_value.delete.assert_called_once()


def test_get_task_returns_dict_when_exists():
    mock = MagicMock()
    snap = MagicMock()
    snap.exists = True
    snap.to_dict.return_value = {"id": "t1", "title": "x"}
    mock.collection.return_value.document.return_value.get.return_value = snap
    fc = FirestoreClient(client=mock)
    assert fc.get_task("t1") == {"id": "t1", "title": "x"}


def test_get_task_returns_none_when_missing():
    mock = MagicMock()
    snap = MagicMock()
    snap.exists = False
    mock.collection.return_value.document.return_value.get.return_value = snap
    fc = FirestoreClient(client=mock)
    assert fc.get_task("missing") is None


def test_query_tasks_chains_where_clauses():
    """Recording query: each .where(...) returns a fresh chainable; we
    check that all four filters are applied and the .limit().stream()
    is invoked, and that we get the docs as dicts back.
    """
    mock = MagicMock()
    # Build chain: collection -> q -> q -> q -> q -> q (limit) -> stream()
    q = MagicMock()
    mock.collection.return_value = q
    q.where.return_value = q  # each .where returns the same chainable
    q.limit.return_value = q

    doc1, doc2 = MagicMock(), MagicMock()
    doc1.to_dict.return_value = {"id": "t1"}
    doc2.to_dict.return_value = {"id": "t2"}
    q.stream.return_value = iter([doc1, doc2])

    fc = FirestoreClient(client=mock)
    out = fc.query_tasks(
        assigned_to="scoopy-id",
        completed=False,
        task_type="ACTION",
        due_on_or_before="2026-05-06",
        limit=50,
    )
    assert out == [{"id": "t1"}, {"id": "t2"}]
    # Four filters applied
    where_calls = [c.args for c in q.where.call_args_list]
    assert ("assigned_to", "==", "scoopy-id") in where_calls
    assert ("completed", "==", False) in where_calls
    assert ("task_type", "==", "ACTION") in where_calls
    assert ("due_date", "<=", "2026-05-06") in where_calls
    q.limit.assert_called_once_with(50)


def test_query_tasks_skips_none_filters():
    mock = MagicMock()
    q = MagicMock()
    mock.collection.return_value = q
    q.where.return_value = q
    q.limit.return_value = q
    q.stream.return_value = iter([])

    fc = FirestoreClient(client=mock)
    fc.query_tasks(assigned_to="s")
    # Only one .where call (for assigned_to)
    assert q.where.call_count == 1


def test_lazy_init_raises_when_no_creds(monkeypatch):
    """If no client is injected and creds are missing, accessing .client
    surfaces a useful error rather than silently failing later.
    """
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", raising=False)
    monkeypatch.setattr(fc_mod, "_build_client", lambda: None)
    fc = FirestoreClient()
    with pytest.raises(RuntimeError, match="not available"):
        _ = fc.client
