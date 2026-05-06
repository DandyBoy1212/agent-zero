from approval import ApprovalStore, default_store
from skill_mem0_save_candidate import mem0_save_candidate


def test_save_candidate_queues_card_with_correct_action_type(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
    # Snapshot default store length to confirm it queued (and not in test store)
    initial = len(default_store.list_pending())
    result = mem0_save_candidate(
        contact_id="abc123",
        namespace="contact:abc123",
        fact="Mrs Jenkins prefers WhatsApp over SMS",
        why_save="stated preference; impacts how we contact her",
    )
    assert "approval_token" in result
    assert result["status"] == "queued"
    pending = default_store.list_pending()
    assert len(pending) == initial + 1
    _, card = pending[-1]
    assert card["action_type"] == "memory_candidate"
    assert card["contact_id"] == "abc123"
    assert card["draft"].startswith("Mrs Jenkins")
    assert card["reasoning"].startswith("stated preference")


def test_save_candidate_pending_action_is_mem0_persist(monkeypatch):
    monkeypatch.setenv("SCOOPY_AUTO_APPROVE", "0")
    # Use the default store but verify the action that would run on approve
    initial = len(default_store.list_pending())
    mem0_save_candidate(
        contact_id="c2",
        namespace="business:scoop_patrol",
        fact="Cancellation requires 7-day notice",
        why_save="repeated owner clarification in chats",
    )
    pending = default_store.list_pending()
    assert len(pending) == initial + 1
    _, card = pending[-1]
    actions = card["pending_actions"]
    assert len(actions) == 1
    assert actions[0]["skill"] == "mem0_persist"
    assert actions[0]["args"]["namespace"] == "business:scoop_patrol"
    assert actions[0]["args"]["fact"] == "Cancellation requires 7-day notice"
