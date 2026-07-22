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


def test_pending_cards_survive_a_restart(tmp_path):
    """A card raised at 3am must still exist at 8am. Scoopy restarts on every
    deploy; this morning he restarted eight times in twenty minutes."""
    path = tmp_path / "approvals.json"
    store = ApprovalStore(ttl_seconds=3600, path=str(path))
    token = store.issue(card={"summary": "Add sanitisation for Karen Mitchell?"})

    # A completely fresh process, same file.
    revived = ApprovalStore(ttl_seconds=3600, path=str(path))
    card = revived.consume(token)
    assert card["summary"] == "Add sanitisation for Karen Mitchell?"


def test_a_consumed_card_stays_consumed_across_a_restart(tmp_path):
    path = tmp_path / "approvals.json"
    store = ApprovalStore(ttl_seconds=3600, path=str(path))
    token = store.issue(card={"summary": "x"})
    store.consume(token)

    revived = ApprovalStore(ttl_seconds=3600, path=str(path))
    with pytest.raises(ApprovalError):
        revived.consume(token)


def test_expiry_is_honoured_across_a_restart(tmp_path):
    path = tmp_path / "approvals.json"
    store = ApprovalStore(ttl_seconds=0, path=str(path))
    token = store.issue(card={"summary": "x"})
    time.sleep(0.01)
    revived = ApprovalStore(ttl_seconds=0, path=str(path))
    with pytest.raises(ApprovalError):
        revived.consume(token)


def test_a_corrupt_store_file_does_not_crash_startup(tmp_path):
    """Fail toward an empty store, never toward a crash loop. A malformed file
    must not stop Scoopy booting."""
    path = tmp_path / "approvals.json"
    path.write_text("{ this is not json", encoding="utf-8")
    store = ApprovalStore(ttl_seconds=60, path=str(path))
    assert store.list_pending() == []


def test_in_memory_mode_still_works_with_no_path():
    """Every existing test constructs without a path. That must keep working."""
    store = ApprovalStore(ttl_seconds=60)
    token = store.issue(card={"a": 1})
    assert store.consume(token) == {"a": 1}
