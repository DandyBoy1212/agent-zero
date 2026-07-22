import pytest
from unittest.mock import MagicMock, patch
from approval import ApprovalStore
from skill_notify_owner import notify_owner


def test_notify_owner_returns_token_and_queues_card(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
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
    assert result["auto_approved"] is False
    pending = store.list_pending()
    assert len(pending) == 1
    _, card = pending[0]
    assert card["draft"].startswith("Hi Mrs Jenkins")
    assert card["action_type"] == "in_scope"
    assert card["contact_id"] == "c1"
    assert card["pending_actions"][0]["skill"] == "ghl_send_message"


def test_notify_owner_uses_default_store_when_none_passed(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
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


def test_action_type_drift_supported(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
    store = ApprovalStore()
    result = notify_owner(
        store=store, contact_id="c1", draft="holding response",
        reasoning="customer wants to cancel - out of scope",
        action_type="drift",
        pending_actions=[{"skill": "ghl_send_message", "args": {"contact_id": "c1", "message": "thanks for letting us know..."}}],
    )
    _, card = store.list_pending()[0]
    assert card["action_type"] == "drift"


def test_action_type_memory_candidate_supported(monkeypatch):
    """Memory curation cards use action_type='memory_candidate' with no draft.
    The 'draft' field carries the candidate fact."""
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
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


def test_pending_actions_can_be_empty_for_pure_escalation(monkeypatch):
    """Sometimes the agent just wants to flag something to the owner with no
    suggested action. Card has empty pending_actions; approving is a no-op."""
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
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


def test_notify_owner_auto_approves_when_env_set(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "1")
    import dispatcher
    fake_skill = MagicMock(return_value={"status": "success"})
    monkeypatch.setitem(dispatcher.SKILL_REGISTRY, "_test_skill", fake_skill)

    store = ApprovalStore()
    with patch("ghl_client.GhlClient") as fake_client_cls:
        fake_client_cls.return_value = MagicMock()
        result = notify_owner(
            store=store,
            contact_id="c1", draft="x", reasoning="r",
            action_type="in_scope",
            pending_actions=[{"skill": "_test_skill", "args": {"contact_id": "c1"}}],
        )
    assert result["status"] == "executed"
    assert result["auto_approved"] is True
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "success"
    fake_skill.assert_called_once()


def test_notify_owner_queues_when_env_zero(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
    store = ApprovalStore()
    result = notify_owner(
        store=store,
        contact_id="c1", draft="x", reasoning="r",
        action_type="in_scope",
        pending_actions=[],
    )
    assert result["status"] == "queued"
    assert result["auto_approved"] is False


def test_card_carries_a_human_summary_and_the_money():
    store = ApprovalStore(ttl_seconds=60)
    notify_owner(
        store=store,
        contact_id="abc123",
        draft="",
        reasoning="operator asked to add sanitisation",
        action_type="in_scope",
        pending_actions=[{"skill": "ghl_field_update", "args": {}}],
        summary="Add sanitisation for Karen Mitchell?",
        detail="Adds £12.00 per month. Next bill goes from £48.00 to £60.00.",
        customer_name="Karen Mitchell",
        trigger_context="asked",
    )
    (_token, card), = store.list_pending()
    assert card["summary"] == "Add sanitisation for Karen Mitchell?"
    assert card["detail"] == "Adds £12.00 per month. Next bill goes from £48.00 to £60.00."
    assert card["customer_name"] == "Karen Mitchell"
    assert card["trigger_context"] == "asked"


def test_existing_call_sites_keep_working_without_the_new_fields():
    """Every current caller omits these. They must default, not explode."""
    store = ApprovalStore(ttl_seconds=60)
    notify_owner(
        store=store,
        contact_id="abc123",
        draft="Hi Karen, just confirming.",
        reasoning="reply to customer",
        action_type="in_scope",
        pending_actions=[{"skill": "ghl_send_message", "args": {}}],
    )
    (_token, card), = store.list_pending()
    assert card["summary"] == ""
    assert card["trigger_context"] == "unknown"


def test_trigger_context_is_validated():
    store = ApprovalStore(ttl_seconds=60)
    with pytest.raises(ValueError):
        notify_owner(
            store=store, contact_id="a", draft="", reasoning="r",
            action_type="in_scope", pending_actions=[],
            trigger_context="whenever",
        )


def test_auto_approve_is_off_by_default(monkeypatch, tmp_path):
    """Stage one of the trust ladder: everything asks. The old default was ON,
    which meant Scoopy executed without asking and, because the setting lived
    in tmp/, silently returned to executing after every restart."""
    import skill_notify_owner as sno

    monkeypatch.setattr(sno, "_RUNTIME_FILE", tmp_path / "runtime.json")
    monkeypatch.delenv("SCOOPY_AUTO_APPROVE", raising=False)
    assert sno._auto_approve_enabled() is False


def test_auto_approve_setting_lives_on_the_persistent_disk():
    """tmp/ is wiped on every restart; usr/ is the mounted disk. A safety
    setting that resets itself to the unsafe value is worse than none."""
    import skill_notify_owner as sno

    assert "usr" in str(sno._RUNTIME_FILE).replace("\\", "/").split("/")
    assert "tmp" not in str(sno._RUNTIME_FILE).replace("\\", "/").split("/")
