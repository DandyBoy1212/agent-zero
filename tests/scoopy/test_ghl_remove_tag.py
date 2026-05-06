from unittest.mock import MagicMock, patch
from skill_ghl_remove_tag import ghl_remove_tag


@patch("skill_ghl_remove_tag.post_auto_note")
def test_remove_tag_calls_delete_then_auto_note(mock_note):
    client = MagicMock()
    client.delete.return_value = MagicMock(status_code=200, json=lambda: {"ok": True}, text="ok")
    mock_note.return_value = True
    result = ghl_remove_tag(
        client=client,
        contact_id="c1",
        tag_name="vip",
        reasoning="Customer downgraded",
        approver="liam",
    )
    assert result["status"] == "success"
    assert result["tag"] == "vip"
    call = client.delete.call_args
    assert call.args[0] == "/contacts/c1/tags"
    assert call.kwargs["payload"] == {"tags": ["vip"]}
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert kwargs["action_name"] == "ghl_remove_tag"
    assert "vip" in kwargs["payload_summary"]


@patch("skill_ghl_remove_tag.post_auto_note")
def test_remove_tag_logs_failure(mock_note):
    client = MagicMock()
    client.delete.return_value = MagicMock(status_code=500, text="server error", json=lambda: {})
    mock_note.return_value = True
    result = ghl_remove_tag(
        client=client, contact_id="c1", tag_name="vip",
        reasoning="r", approver="liam",
    )
    assert result["status"] == "error"
    assert result["code"] == 500
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert "error" in kwargs["result"]
    assert "500" in kwargs["result"]
