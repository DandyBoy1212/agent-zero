from unittest.mock import MagicMock, patch
import pytest
from skill_ghl_search_contact import ghl_search_contact


def test_search_contact_returns_list(monkeypatch):
    monkeypatch.setenv("GHL_LOCATION_ID", "loc-123")
    client = MagicMock()
    client.search_contacts.return_value = [
        {"id": "c1", "firstName": "Mrs", "lastName": "Jenkins", "contactName": "Mrs Jenkins"},
        {"id": "c2", "firstName": "Bob", "lastName": "Jenkins", "contactName": "Bob Jenkins"},
    ]
    result = ghl_search_contact(client=client, query="Jenkins")
    assert len(result) == 2
    assert result[0]["id"] == "c1"
    client.search_contacts.assert_called_once_with(
        query="Jenkins", location_id="loc-123", limit=10
    )


def test_search_contact_passes_custom_limit(monkeypatch):
    monkeypatch.setenv("GHL_LOCATION_ID", "loc-123")
    client = MagicMock()
    client.search_contacts.return_value = []
    ghl_search_contact(client=client, query="x", limit=5)
    client.search_contacts.assert_called_once_with(
        query="x", location_id="loc-123", limit=5
    )


def test_search_contact_empty_results(monkeypatch):
    monkeypatch.setenv("GHL_LOCATION_ID", "loc-123")
    client = MagicMock()
    client.search_contacts.return_value = []
    result = ghl_search_contact(client=client, query="nobody")
    assert result == []
