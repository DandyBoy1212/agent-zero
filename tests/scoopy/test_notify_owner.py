import pytest
from approval import ApprovalStore
from skill_notify_owner import notify_owner


def test_notify_owner_returns_token_and_queues_card():
    store = ApprovalStore()
    result = notify_owner(
        store=store,
        contact_id="c1",
        draft="Hi Mrs Jenkins, here is your invoice link...",
        reasoning="Customer asked how to pay; in scope",
        action_type="in_scope",
        pending_actions=[
            {"skill": "ghl_send_message", "args": {"contact_id": "c1", "message": "Hi..."}}
        ],
    )
    assert "approval_token" in result
    assert result["status"] == "queued"
    pending = store.list_pending()
    assert len(pending) == 1
    _, card = pending[0]
    assert card["draft"].startswith("Hi Mrs Jenkins")
    assert card["action_type"] == "in_scope"
    assert card["contact_id"] == "c1"
    assert card["pending_actions"][0]["skill"] == "ghl_send_message"


def test_notify_owner_uses_default_store_when_none_passed():
    from approval import default_store
    initial = len(default_store.list_pending())
    notify_owner(
        contact_id="c2",
        draft="msg",
        reasoning="test",
        action_type="drift",
        pending_actions=[],
    )
    assert len(default_store.list_pending()) == initial + 1


def test_action_type_drift_supported():
    store = ApprovalStore()
    result = notify_owner(
        store=store, contact_id="c1", draft="holding response",
        reasoning="customer wants to cancel - out of scope",
        action_type="drift",
        pending_actions=[{"skill": "ghl_send_message", "args": {"contact_id": "c1", "message": "thanks for letting us know..."}}],
    )
    _, card = store.list_pending()[0]
    assert card["action_type"] == "drift"


def test_action_type_memory_candidate_supported():
    """Memory curation cards use action_type='memory_candidate' with no draft.
    The 'draft' field carries the candidate fact."""
    store = ApprovalStore()
    result = notify_owner(
        store=store, contact_id="c1",
        draft="Mrs Jenkins prefers WhatsApp over SMS",
        reasoning="mentioned in last 3 conversations",
        action_type="memory_candidate",
        pending_actions=[{"skill": "mem0_persist", "args": {"namespace": "contact:c1", "fact": "..."}}],
    )
    _, card = store.list_pending()[0]
    assert card["action_type"] == "memory_candidate"


def test_pending_actions_can_be_empty_for_pure_escalation():
    """Sometimes the agent just wants to flag something to the owner with no
    suggested action. Card has empty pending_actions; approving is a no-op."""
    store = ApprovalStore()
    result = notify_owner(
        store=store, contact_id="c1",
        draft="(none)",
        reasoning="unfamiliar request - need owner judgment",
        action_type="escalation",
        pending_actions=[],
    )
    _, card = store.list_pending()[0]
    assert card["pending_actions"] == []
