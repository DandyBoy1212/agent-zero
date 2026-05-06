from unittest.mock import MagicMock, patch
from skill_ghl_field_update import ghl_field_update, _FIELD_NAME_TO_ID


@patch("skill_ghl_field_update.post_auto_note")
def test_field_update_with_named_field_maps_to_id(mock_note):
    client = MagicMock()
    client.put.return_value = MagicMock(status_code=200, json=lambda: {"ok": True}, text="ok")
    mock_note.return_value = True
    result = ghl_field_update(
        client=client,
        contact_id="c1",
        field_updates={"payment_frequency": "Monthly"},
        reasoning="Customer requested change",
        approver="liam",
    )
    assert result["status"] == "success"
    call = client.put.call_args
    assert call.args[0] == "/contacts/c1"
    payload = call.kwargs["payload"]
    # Format: {"customFields": [{"id": ..., "value": ...}]}
    assert "customFields" in payload
    fields = payload["customFields"]
    assert isinstance(fields, list)
    assert any(
        f["id"] == _FIELD_NAME_TO_ID["payment_frequency"] and f["value"] == "Monthly"
        for f in fields
    )
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert kwargs["action_name"] == "ghl_field_update"
    assert "payment_frequency=Monthly" in kwargs["payload_summary"]


@patch("skill_ghl_field_update.post_auto_note")
def test_field_update_with_raw_id_passes_through(mock_note):
    client = MagicMock()
    client.put.return_value = MagicMock(status_code=200, json=lambda: {"ok": True}, text="ok")
    mock_note.return_value = True
    raw_id = "BEkIldTfzjiLn7DXj2Io"  # Next Service Date
    result = ghl_field_update(
        client=client,
        contact_id="c1",
        field_updates={raw_id: "2026-05-15"},
        reasoning="r",
        approver="liam",
    )
    assert result["status"] == "success"
    call = client.put.call_args
    fields = call.kwargs["payload"]["customFields"]
    assert any(f["id"] == raw_id and f["value"] == "2026-05-15" for f in fields)


@patch("skill_ghl_field_update.post_auto_note")
def test_field_update_logs_failure(mock_note):
    client = MagicMock()
    client.put.return_value = MagicMock(status_code=500, text="boom", json=lambda: {})
    mock_note.return_value = True
    result = ghl_field_update(
        client=client, contact_id="c1",
        field_updates={"payment_frequency": "Monthly"},
        reasoning="r", approver="liam",
    )
    assert result["status"] == "error"
    assert result["code"] == 500
    mock_note.assert_called_once()
    kwargs = mock_note.call_args.kwargs
    assert "error" in kwargs["result"]
