from unittest.mock import MagicMock
from skill_mem0_search import mem0_search


def test_mem0_search_passes_namespace_and_query_through():
    fake_client = MagicMock()
    fake_client.search.return_value = [
        {"id": "m1", "memory": "Mrs Jenkins prefers WhatsApp"},
    ]
    out = mem0_search(
        namespace="contact:abc",
        query="payment preferences",
        limit=3,
        client=fake_client,
    )
    assert out == [{"id": "m1", "memory": "Mrs Jenkins prefers WhatsApp"}]
    fake_client.search.assert_called_once_with(
        namespace="contact:abc", query="payment preferences", limit=3
    )


def test_mem0_search_empty_namespace_returns_empty_without_calling_client():
    fake_client = MagicMock()
    out = mem0_search(namespace="", query="anything", client=fake_client)
    assert out == []
    fake_client.search.assert_not_called()
