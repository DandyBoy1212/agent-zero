from unittest.mock import MagicMock
import os
import pytest
from skills_ghl_get import (
    ghl_get_contact, ghl_get_tasks_for_contact, ghl_get_conversation,
)


def test_get_contact_returns_payload():
    client = MagicMock()
    client.get_contact.return_value = {"contact": {"id": "c1", "firstName": "Sarah"}}
    result = ghl_get_contact(client=client, contact_id="c1")
    assert result["contact"]["firstName"] == "Sarah"
    client.get_contact.assert_called_once_with("c1")


def test_get_tasks_returns_all_open_tasks_by_default():
    client = MagicMock()
    client.get_tasks_for_contact.return_value = [
        {"id": "t1", "title": "[REPLY] x", "assignedTo": "scoopy-id", "completed": False},
        {"id": "t2", "title": "Other",     "assignedTo": "liam-id",   "completed": False},
        {"id": "t3", "title": "Done",      "assignedTo": "scoopy-id", "completed": True},
    ]
    result = ghl_get_tasks_for_contact(client=client, contact_id="c1")
    # Default: all open (incomplete) tasks regardless of assignment
    assert len(result) == 2
    assert {t["id"] for t in result} == {"t1", "t2"}


def test_get_tasks_filters_to_scoopy_when_requested(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    client = MagicMock()
    client.get_tasks_for_contact.return_value = [
        {"id": "t1", "title": "[REPLY] x", "assignedTo": "scoopy-id", "completed": False},
        {"id": "t2", "title": "Other",     "assignedTo": "liam-id",   "completed": False},
    ]
    result = ghl_get_tasks_for_contact(client=client, contact_id="c1", assigned_to_scoopy_only=True)
    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_get_tasks_filters_by_title_prefix():
    client = MagicMock()
    client.get_tasks_for_contact.return_value = [
        {"id": "t1", "title": "[REPLY] follow up", "assignedTo": "x", "completed": False},
        {"id": "t2", "title": "[ACTION] cancel",   "assignedTo": "x", "completed": False},
        {"id": "t3", "title": "no prefix",          "assignedTo": "x", "completed": False},
    ]
    reply = ghl_get_tasks_for_contact(client=client, contact_id="c1", title_prefix="[REPLY]")
    assert len(reply) == 1 and reply[0]["id"] == "t1"
    action = ghl_get_tasks_for_contact(client=client, contact_id="c1", title_prefix="[ACTION]")
    assert len(action) == 1 and action[0]["id"] == "t2"


def test_get_tasks_combines_filters(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    client = MagicMock()
    client.get_tasks_for_contact.return_value = [
        {"id": "t1", "title": "[REPLY] x", "assignedTo": "scoopy-id", "completed": False},
        {"id": "t2", "title": "[REPLY] y", "assignedTo": "liam-id",   "completed": False},
        {"id": "t3", "title": "[ACTION] z", "assignedTo": "scoopy-id", "completed": False},
    ]
    result = ghl_get_tasks_for_contact(
        client=client, contact_id="c1",
        assigned_to_scoopy_only=True, title_prefix="[REPLY]",
    )
    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_get_conversation_returns_messages():
    client = MagicMock()
    client.get_conversation.return_value = {"messages": [{"id": "m1", "body": "hi"}]}
    result = ghl_get_conversation(client=client, conversation_id="conv1")
    assert "messages" in result
    client.get_conversation.assert_called_once_with("conv1")
