from unittest.mock import MagicMock, patch
from skill_mem0_persist import mem0_persist


@patch("skill_mem0_persist.post_auto_note")
def test_persist_calls_mem0_add_with_metadata_and_auto_notes_for_contact_namespace(
    mock_note,
):
    mock_note.return_value = True
    fake_mc = MagicMock()
    fake_mc.add.return_value = {"id": "mem-xyz"}
    ghl_client = MagicMock()
    result = mem0_persist(
        namespace="contact:abc123",
        fact="Mrs Jenkins prefers WhatsApp",
        reasoning="stated preference",
        approver="liam",
        client=ghl_client,
        mem0_client=fake_mc,
    )
    assert result["status"] == "success"
    assert result["memory_id"] == "mem-xyz"
    assert result["namespace"] == "contact:abc123"

    # mem0 add was called correctly
    fake_mc.add.assert_called_once()
    kwargs = fake_mc.add.call_args.kwargs
    assert kwargs["namespace"] == "contact:abc123"
    assert kwargs["fact"] == "Mrs Jenkins prefers WhatsApp"
    metadata = kwargs["metadata"]
    assert metadata["approved_by"] == "liam"
    assert metadata["reason"] == "stated preference"
    assert "saved_at" in metadata

    # Auto-note posted on the contact (contact-scoped namespace)
    mock_note.assert_called_once()
    note_kwargs = mock_note.call_args.kwargs
    assert note_kwargs["contact_id"] == "abc123"
    assert note_kwargs["action_name"] == "mem0_persist"
    assert note_kwargs["approver"] == "liam"
    assert "mem-xyz" in note_kwargs["result"]
    assert "Mrs Jenkins prefers WhatsApp" in note_kwargs["payload_summary"]


@patch("skill_mem0_persist.post_auto_note")
def test_persist_does_not_auto_note_for_business_namespace(mock_note):
    mock_note.return_value = True
    fake_mc = MagicMock()
    fake_mc.add.return_value = {"id": "mem-biz"}
    result = mem0_persist(
        namespace="business:scoop_patrol",
        fact="Cancellation requires 7-day notice",
        reasoning="repeated clarification",
        approver="liam",
        client=MagicMock(),
        mem0_client=fake_mc,
    )
    assert result["status"] == "success"
    assert result["memory_id"] == "mem-biz"
    mock_note.assert_not_called()


@patch("skill_mem0_persist.post_auto_note")
def test_persist_does_not_auto_note_for_procedures_namespace(mock_note):
    mock_note.return_value = True
    fake_mc = MagicMock()
    fake_mc.add.return_value = {"id": "mem-proc"}
    mem0_persist(
        namespace="procedures:scoop_patrol",
        fact="Payment chase: send link, wait 48h, escalate",
        reasoning="standard flow",
        approver="liam",
        client=MagicMock(),
        mem0_client=fake_mc,
    )
    mock_note.assert_not_called()


@patch("skill_mem0_persist.post_auto_note")
def test_persist_logs_failure_on_contact_namespace(mock_note):
    mock_note.return_value = True
    fake_mc = MagicMock()
    fake_mc.add.side_effect = RuntimeError("mem0 down")
    result = mem0_persist(
        namespace="contact:abc123",
        fact="x",
        reasoning="r",
        approver="liam",
        client=MagicMock(),
        mem0_client=fake_mc,
    )
    assert result["status"] == "error"
    assert "mem0 down" in result["reason"]
    mock_note.assert_called_once()
    note_kwargs = mock_note.call_args.kwargs
    assert "error" in note_kwargs["result"]
