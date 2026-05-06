from unittest.mock import MagicMock, patch
from skill_ghl_update_task import ghl_update_task


@patch("skill_ghl_update_task.post_auto_note")
def test_update_task_marks_complete(mock_note):
    client = MagicMock()
    client.put.return_value = MagicMock(status_code=200, json=lambda: {"id": "task-1"}, text="ok")
    mock_note.return_value = True
    result = ghl_update_task(
        client=client,
        contact_id="c1",
        task_id="task-1",
        completed=True,
        body="Customer replied — closing.",
        reasoning="Reply received",
        approver="liam",
    )
    assert result["status"] == "success"
    call = client.put.call_args
    assert call.args[0] == "/contacts/c1/tasks/task-1"
    payload = call.kwargs["payload"]
    assert payload == {"completed": True, "body": "Customer replied — closing."}
    # title/dueDate not present (None values omitted)
    assert "title" not in payload
    assert "dueDate" not in payload
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert kwargs["action_name"] == "ghl_update_task"
    assert "completed=True" in kwargs["payload_summary"]


@patch("skill_ghl_update_task.post_auto_note")
def test_update_task_change_title_and_due(mock_note):
    client = MagicMock()
    client.put.return_value = MagicMock(status_code=200, json=lambda: {}, text="ok")
    mock_note.return_value = True
    result = ghl_update_task(
        client=client,
        contact_id="c1",
        task_id="t1",
        title="[ACTION] Updated title",
        due_date="2026-06-01",
        reasoning="Reschedule",
        approver="liam",
    )
    assert result["status"] == "success"
    payload = client.put.call_args.kwargs["payload"]
    assert payload["title"] == "[ACTION] Updated title"
    assert payload["dueDate"] == "2026-06-01"
    assert "completed" not in payload
    assert "body" not in payload


@patch("skill_ghl_update_task.post_auto_note")
def test_update_task_logs_failure(mock_note):
    client = MagicMock()
    client.put.return_value = MagicMock(status_code=500, text="boom", json=lambda: {})
    mock_note.return_value = True
    result = ghl_update_task(
        client=client, contact_id="c1", task_id="t1",
        completed=True, reasoning="r", approver="liam",
    )
    assert result["status"] == "error"
    assert result["code"] == 500
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert "error" in kwargs["result"]
