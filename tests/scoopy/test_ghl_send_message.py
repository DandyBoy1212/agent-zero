from unittest.mock import MagicMock, patch
from skill_ghl_send_message import ghl_send_message


@patch("skill_ghl_send_message.post_auto_note")
def test_send_message_posts_message_then_auto_note(mock_note):
    client = MagicMock()
    client.post.return_value = MagicMock(status_code=201, json=lambda: {"messageId": "m1"})
    mock_note.return_value = True
    result = ghl_send_message(
        client=client,
        contact_id="c1",
        message="Hi Mrs Jenkins...",
        reasoning="In scope per task",
        approver="liam",
    )
    assert result["status"] == "success"
    assert result["message_id"] == "m1"
    # Verify message POST happened to /conversations/messages
    sent_paths = [c.args[0] for c in client.post.call_args_list]
    assert "/conversations/messages" in sent_paths
    # Auto-note was posted
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert kwargs["action_name"] == "ghl_send_message"
    assert kwargs["contact_id"] == "c1"
    assert kwargs["approver"] == "liam"
    assert "Hi Mrs Jenkins" in kwargs["payload_summary"]


@patch("skill_ghl_send_message.post_auto_note")
def test_send_message_logs_failure_with_status_code(mock_note):
    client = MagicMock()
    client.post.return_value = MagicMock(status_code=500, text="server error", json=lambda: {})
    mock_note.return_value = True
    result = ghl_send_message(
        client=client, contact_id="c1", message="hi",
        reasoning="r", approver="liam",
    )
    assert result["status"] == "error"
    assert result["code"] == 500
    # Auto-note still fired with the error
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert "error" in kwargs["result"]
    assert "500" in kwargs["result"]
