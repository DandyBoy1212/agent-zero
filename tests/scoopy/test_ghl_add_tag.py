from unittest.mock import MagicMock, patch
from skill_ghl_add_tag import ghl_add_tag


@patch("skill_ghl_add_tag.post_auto_note")
def test_add_tag_posts_tag_then_auto_note(mock_note):
    client = MagicMock()
    client.post.return_value = MagicMock(status_code=200, json=lambda: {"ok": True}, text="ok")
    mock_note.return_value = True
    result = ghl_add_tag(
        client=client,
        contact_id="c1",
        tag_name="vip",
        reasoning="Customer is high value",
        approver="liam",
    )
    assert result["status"] == "success"
    assert result["tag"] == "vip"
    # POST went to /contacts/{id}/tags with payload
    call = client.post.call_args
    assert call.args[0] == "/contacts/c1/tags"
    assert call.kwargs["payload"] == {"tags": ["vip"]}
    # Auto-note posted
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert kwargs["action_name"] == "ghl_add_tag"
    assert kwargs["contact_id"] == "c1"
    assert kwargs["approver"] == "liam"
    assert "vip" in kwargs["payload_summary"]


@patch("skill_ghl_add_tag.post_auto_note")
def test_add_tag_logs_failure(mock_note):
    client = MagicMock()
    client.post.return_value = MagicMock(status_code=500, text="server error", json=lambda: {})
    mock_note.return_value = True
    result = ghl_add_tag(
        client=client, contact_id="c1", tag_name="vip",
        reasoning="r", approver="liam",
    )
    assert result["status"] == "error"
    assert result["code"] == 500
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert "error" in kwargs["result"]
    assert "500" in kwargs["result"]
