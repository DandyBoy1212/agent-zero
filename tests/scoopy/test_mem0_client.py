from unittest.mock import MagicMock
import pytest
from mem0_client import Mem0Client


def test_search_passes_namespace_as_a_filter_not_a_top_level_kwarg():
    """mem0ai 2.x rejects user_id as a top-level search kwarg:

        Top-level entity parameters frozenset({'user_id'}) are not supported
        in search(). Use filters={'user_id': '...'} instead.

    This test previously asserted the OLD shape, so it passed for months while
    every search Scoopy ran failed in production. It was verifying that the
    code did what it did, rather than that it worked.
    """
    inner = MagicMock()
    inner.search.return_value = [{"id": "m1", "memory": "fact"}]
    mc = Mem0Client(api_key="x", client=inner)
    out = mc.search(namespace="contact:abc", query="payment", limit=3)
    assert out == [{"id": "m1", "memory": "fact"}]
    args, kwargs = inner.search.call_args
    assert args[0] == "payment"
    opts = kwargs["options"]
    # Must be the pydantic model, not a dict shaped like it: the SDK calls
    # .model_dump() on it and a dict raises AttributeError. Both shapes have
    # now failed in production, so assert the type as well as the values.
    assert hasattr(opts, "model_dump"), f"options must be a pydantic model, got {type(opts)}"
    assert opts.filters == {"user_id": "contact:abc"}
    assert opts.top_k == 3


def test_search_never_passes_user_id_at_the_top_level():
    """Guard against a well-meaning revert. This is the exact call that errors."""
    inner = MagicMock()
    inner.search.return_value = []
    Mem0Client(api_key="x", client=inner).search(namespace="business:scoop_patrol", query="gate code")
    _, kwargs = inner.search.call_args
    assert "user_id" not in kwargs
    assert "limit" not in kwargs


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
