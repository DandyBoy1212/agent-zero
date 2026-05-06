from unittest.mock import MagicMock
import pytest
from mem0_client import Mem0Client


def test_search_passes_namespace_as_user_id():
    inner = MagicMock()
    inner.search.return_value = [{"id": "m1", "memory": "fact"}]
    mc = Mem0Client(api_key="x", client=inner)
    out = mc.search(namespace="contact:abc", query="payment", limit=3)
    assert out == [{"id": "m1", "memory": "fact"}]
    inner.search.assert_called_once_with(
        query="payment", user_id="contact:abc", limit=3
    )


def test_search_normalizes_dict_response_with_results_key():
    inner = MagicMock()
    inner.search.return_value = {
        "results": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}]
    }
    mc = Mem0Client(api_key="x", client=inner)
    out = mc.search(namespace="business:scoop_patrol", query="q", limit=2)
    assert out == [{"id": "m1"}, {"id": "m2"}]


def test_search_normalizes_dict_response_with_memories_key():
    inner = MagicMock()
    inner.search.return_value = {"memories": [{"id": "m1"}]}
    mc = Mem0Client(api_key="x", client=inner)
    out = mc.search(namespace="contact:abc", query="q")
    assert out == [{"id": "m1"}]


def test_search_returns_empty_list_for_empty_namespace():
    inner = MagicMock()
    mc = Mem0Client(api_key="x", client=inner)
    assert mc.search(namespace="", query="q") == []
    inner.search.assert_not_called()


def test_search_returns_empty_list_for_no_results():
    inner = MagicMock()
    inner.search.return_value = None
    mc = Mem0Client(api_key="x", client=inner)
    assert mc.search(namespace="contact:abc", query="q") == []


def test_add_passes_namespace_and_metadata():
    inner = MagicMock()
    inner.add.return_value = {"id": "mem-123"}
    mc = Mem0Client(api_key="x", client=inner)
    out = mc.add(
        namespace="contact:abc",
        fact="prefers WhatsApp",
        metadata={"approved_by": "liam"},
    )
    assert out == {"id": "mem-123"}
    inner.add.assert_called_once_with(
        messages=[{"role": "user", "content": "prefers WhatsApp"}],
        user_id="contact:abc",
        metadata={"approved_by": "liam"},
    )
