from unittest.mock import MagicMock
import pytest

import skill_ghl_list_watching as mod
from skill_ghl_list_watching import ghl_list_watching_contacts


def _fake_contacts():
    return [
        {
            "id": "c1",
            "firstName": "Mrs",
            "lastName": "Jenkins",
            "phone": "+447111000001",
            "email": "j@example.com",
            "tags": ["scoopy-watching", "weekly"],
        },
        {
            "id": "c2",
            "firstName": "",
            "lastName": "",
            "contactName": "Bob Smith",
            "phone": None,
            "email": None,
            "tags": ["scoopy-watching"],
        },
    ]


def test_list_watching_contacts_with_tasks(monkeypatch):
    client = MagicMock()
    client.search_contacts_by_tag.return_value = _fake_contacts()

    fake_tasks_by_contact = {
        "c1": [{"id": "t1", "title": "[REPLY] Mrs Jenkins follow-up"}],
        "c2": [],
    }

    def fake_get_tasks(*, client, contact_id, assigned_to_scoopy_only=False, **_):
        assert assigned_to_scoopy_only is True
        return fake_tasks_by_contact[contact_id]

    monkeypatch.setattr(mod, "ghl_get_tasks_for_contact", fake_get_tasks)

    result = ghl_list_watching_contacts(client=client, include_tasks=True)
    assert len(result) == 2
    assert result[0]["id"] == "c1"
    assert result[0]["name"] == "Mrs Jenkins"
    assert result[0]["tasks"] == fake_tasks_by_contact["c1"]
    # contact with no firstName/lastName should fall back to contactName
    assert result[1]["name"] == "Bob Smith"
    assert result[1]["tasks"] == []
    client.search_contacts_by_tag.assert_called_once_with(tag="scoopy-watching")


def test_list_watching_contacts_without_tasks(monkeypatch):
    client = MagicMock()
    client.search_contacts_by_tag.return_value = _fake_contacts()

    # Sentinel: must not be called when include_tasks=False
    called = {"n": 0}

    def fake_get_tasks(*args, **kwargs):
        called["n"] += 1
        return []

    monkeypatch.setattr(mod, "ghl_get_tasks_for_contact", fake_get_tasks)

    result = ghl_list_watching_contacts(client=client, include_tasks=False)
    assert len(result) == 2
    assert "tasks" not in result[0]
    assert called["n"] == 0


def test_list_watching_contacts_empty():
    client = MagicMock()
    client.search_contacts_by_tag.return_value = []
    assert ghl_list_watching_contacts(client=client) == []


def test_list_watching_contacts_custom_tag(monkeypatch):
    client = MagicMock()
    client.search_contacts_by_tag.return_value = []
    ghl_list_watching_contacts(
        client=client, include_tasks=False, tag="rescue-pending"
    )
    client.search_contacts_by_tag.assert_called_once_with(tag="rescue-pending")


def test_list_watching_contacts_fallback_when_no_by_tag_method(monkeypatch):
    """If the client lacks search_contacts_by_tag, fall back to query+filter."""
    monkeypatch.setenv("GHL_LOCATION_ID", "loc-xyz")

    class LegacyClient:
        def __init__(self):
            self.calls = []

        def search_contacts(self, *, query, location_id, limit):
            self.calls.append((query, location_id, limit))
            return [
                {"id": "c1", "firstName": "A", "lastName": "B", "tags": ["scoopy-watching"]},
                {"id": "c2", "firstName": "C", "lastName": "D", "tags": ["other"]},
            ]

    client = LegacyClient()
    result = ghl_list_watching_contacts(client=client, include_tasks=False)
    # only the contact actually tagged scoopy-watching is kept
    assert len(result) == 1
    assert result[0]["id"] == "c1"
    assert client.calls[0] == ("scoopy-watching", "loc-xyz", 100)


def test_list_watching_contacts_swallows_per_contact_task_errors(monkeypatch):
    client = MagicMock()
    client.search_contacts_by_tag.return_value = [
        {"id": "c1", "firstName": "A", "lastName": "B", "tags": ["scoopy-watching"]},
    ]

    def boom(*args, **kwargs):
        raise RuntimeError("ghl 500")

    monkeypatch.setattr(mod, "ghl_get_tasks_for_contact", boom)

    result = ghl_list_watching_contacts(client=client, include_tasks=True)
    assert result[0]["tasks"] == []
    assert "ghl 500" in result[0]["tasks_error"]
