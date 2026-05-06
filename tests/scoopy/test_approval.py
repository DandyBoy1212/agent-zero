import time
import pytest
from approval import ApprovalStore, ApprovalError


def test_issue_returns_unique_tokens():
    store = ApprovalStore(ttl_seconds=60)
    t1 = store.issue(card={"action": "send", "to": "c1"})
    t2 = store.issue(card={"action": "send", "to": "c2"})
    assert t1 != t2
    assert len(t1) >= 16


def test_consume_valid_token_returns_card_then_invalidates():
    store = ApprovalStore(ttl_seconds=60)
    token = store.issue(card={"action": "send"})
    card = store.consume(token)
    assert card == {"action": "send"}
    with pytest.raises(ApprovalError):
        store.consume(token)


def test_expired_token_raises():
    store = ApprovalStore(ttl_seconds=0)
    token = store.issue(card={"action": "send"})
    time.sleep(0.01)
    with pytest.raises(ApprovalError):
        store.consume(token)


def test_unknown_token_raises():
    store = ApprovalStore(ttl_seconds=60)
    with pytest.raises(ApprovalError):
        store.consume("never-issued")


def test_list_pending_returns_only_unexpired():
    store = ApprovalStore(ttl_seconds=60)
    t1 = store.issue(card={"a": 1})
    t2 = store.issue(card={"a": 2})
    pending = store.list_pending()
    assert len(pending) == 2
    tokens = {t for t, _ in pending}
    assert t1 in tokens and t2 in tokens
