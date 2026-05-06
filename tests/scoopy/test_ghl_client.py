import os
from unittest.mock import patch, MagicMock
import pytest
from ghl_client import GhlClient


def test_ghl_client_uses_scoopy_api_key():
    client = GhlClient(api_key="test-key", location_id="loc-1")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Version"] == "2021-07-28"


@patch("ghl_client.httpx.Client.get")
def test_get_contact_calls_correct_url(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"contact": {"id": "c1"}})
    client = GhlClient(api_key="k", location_id="l")
    result = client.get_contact("c1")
    assert mock_get.called
    assert "/contacts/c1" in mock_get.call_args[0][0]
    assert result["contact"]["id"] == "c1"


@patch("ghl_client.httpx.Client.get")
def test_get_tasks_for_contact_returns_tasks_list(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"tasks": [{"id": "t1"}]})
    client = GhlClient(api_key="k", location_id="l")
    tasks = client.get_tasks_for_contact("c1")
    assert "/contacts/c1/tasks" in mock_get.call_args[0][0]
    assert len(tasks) == 1
