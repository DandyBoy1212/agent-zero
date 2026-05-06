from unittest.mock import MagicMock, patch
import pytest
from approval import ApprovalStore, ApprovalError
import dispatcher  # imports module so we can patch SKILL_REGISTRY


def test_dispatcher_consumes_token_and_runs_registered_skill(monkeypatch):
    fake_skill = MagicMock(return_value={"status": "success"})
    monkeypatch.setitem(dispatcher.SKILL_REGISTRY, "_test_skill", fake_skill)
    store = ApprovalStore()
    token = store.issue(card={
        "contact_id": "c1",
        "draft": "msg",
        "reasoning": "r",
        "action_type": "in_scope",
        "pending_actions": [{"skill": "_test_skill", "args": {"contact_id": "c1", "x": 1}}],
    })
    client = MagicMock()
    results = dispatcher.execute_with_approval(
        store=store, token=token, approver="liam", client=client,
    )
    assert results == [{"status": "success"}]
    fake_skill.assert_called_once()
    kwargs = fake_skill.call_args.kwargs
    assert kwargs["client"] is client
    assert kwargs["reasoning"] == "r"
    assert kwargs["approver"] == "liam"
    assert kwargs["x"] == 1
    assert kwargs["contact_id"] == "c1"


def test_dispatcher_rejects_unknown_token():
    store = ApprovalStore()
    with pytest.raises(ApprovalError):
        dispatcher.execute_with_approval(
            store=store, token="bogus", approver="liam", client=MagicMock(),
        )


def test_dispatcher_rejects_reused_token(monkeypatch):
    fake_skill = MagicMock(return_value={"status": "success"})
    monkeypatch.setitem(dispatcher.SKILL_REGISTRY, "_test_skill", fake_skill)
    store = ApprovalStore()
    token = store.issue(card={
        "contact_id": "c1", "draft": "x", "reasoning": "r", "action_type": "in_scope",
        "pending_actions": [{"skill": "_test_skill", "args": {}}],
    })
    dispatcher.execute_with_approval(
        store=store, token=token, approver="liam", client=MagicMock(),
    )
    with pytest.raises(ApprovalError):
        dispatcher.execute_with_approval(
            store=store, token=token, approver="liam", client=MagicMock(),
        )


def test_dispatcher_handles_unknown_skill_name(monkeypatch):
    store = ApprovalStore()
    token = store.issue(card={
        "contact_id": "c1", "draft": "x", "reasoning": "r", "action_type": "in_scope",
        "pending_actions": [{"skill": "no_such_skill", "args": {}}],
    })
    results = dispatcher.execute_with_approval(
        store=store, token=token, approver="liam", client=MagicMock(),
    )
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert "no_such_skill" in results[0]["reason"]


def test_ghl_send_message_is_in_default_registry():
    # Smoke check: ghl_send_message is wired into the default SKILL_REGISTRY
    assert "ghl_send_message" in dispatcher.SKILL_REGISTRY
    assert callable(dispatcher.SKILL_REGISTRY["ghl_send_message"])


def test_all_write_skills_in_default_registry():
    # All six write skills must be wired into the default SKILL_REGISTRY.
    expected = {
        "ghl_send_message",
        "ghl_add_tag",
        "ghl_remove_tag",
        "ghl_create_task",
        "ghl_field_update",
        "ghl_update_task",
    }
    for name in expected:
        assert name in dispatcher.SKILL_REGISTRY, f"{name} missing from registry"
        assert callable(dispatcher.SKILL_REGISTRY[name]), f"{name} not callable"
