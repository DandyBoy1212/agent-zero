import os
from unittest.mock import MagicMock, patch
from skill_ghl_create_task import ghl_create_task


@patch("skill_ghl_create_task.post_auto_note")
def test_create_task_posts_task_then_auto_note(mock_note, monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "user-123")
    client = MagicMock()
    client.post.return_value = MagicMock(
        status_code=201,
        json=lambda: {"id": "task-1", "title": "[ACTION] Follow up"},
        text="ok",
    )
    mock_note.return_value = True
    result = ghl_create_task(
        client=client,
        contact_id="c1",
        title="[ACTION] Follow up",
        body="Check on customer",
        due_date="2026-05-10",
        reasoning="Per customer request",
        approver="liam",
    )
    assert result["status"] == "success"
    assert result["task_id"] == "task-1"
    assert result["title"] == "[ACTION] Follow up"
    # Only one POST (no tag for [ACTION])
    paths = [c.args[0] for c in client.post.call_args_list]
    assert "/contacts/c1/tasks" in paths
    assert "/contacts/c1/tags" not in paths
    # Verify payload
    task_call = next(c for c in client.post.call_args_list if c.args[0] == "/contacts/c1/tasks")
    payload = task_call.kwargs["payload"]
    assert payload["title"] == "[ACTION] Follow up"
    assert payload["body"] == "Check on customer"
    assert payload["dueDate"] == "2026-05-10"
    assert payload["completed"] is False
    assert payload["assignedTo"] == "user-123"
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert kwargs["action_name"] == "ghl_create_task"
    assert "Follow up" in kwargs["payload_summary"]


@patch("skill_ghl_create_task.post_auto_note")
def test_create_task_reply_also_adds_watching_tag(mock_note, monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "user-123")
    client = MagicMock()
    client.post.return_value = MagicMock(
        status_code=201,
        json=lambda: {"id": "task-2"},
        text="ok",
    )
    mock_note.return_value = True
    result = ghl_create_task(
        client=client,
        contact_id="c1",
        title="[REPLY] Awaiting customer reply",
        body="See thread",
        due_date="2026-05-10",
        reasoning="Need reply",
        approver="liam",
    )
    assert result["status"] == "success"
    paths = [c.args[0] for c in client.post.call_args_list]
    assert "/contacts/c1/tasks" in paths
    assert "/contacts/c1/tags" in paths
    tag_call = next(c for c in client.post.call_args_list if c.args[0] == "/contacts/c1/tags")
    assert tag_call.kwargs["payload"] == {"tags": ["scoopy-watching"]}
    # Auto-note called only once (not twice)
    assert mock_note.call_count == 1


@patch("skill_ghl_create_task.post_auto_note")
def test_create_task_logs_failure(mock_note):
    client = MagicMock()
    client.post.return_value = MagicMock(status_code=500, text="boom", json=lambda: {})
    mock_note.return_value = True
    result = ghl_create_task(
        client=client, contact_id="c1",
        title="[ACTION] x", body="b", due_date="2026-05-10",
        reasoning="r", approver="liam", assigned_to="u1",
    )
    assert result["status"] == "error"
    assert result["code"] == 500
    mock_note.assert_called_once()
