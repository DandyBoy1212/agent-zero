from unittest.mock import MagicMock
from auto_note import format_note, post_auto_note


def test_format_note_includes_required_fields():
    note = format_note(
        action_name="ghl_send_message",
        reason="Customer asked how to pay; sent Stripe link per task scope",
        approver="liam",
        result="success: msg_id=abc123",
        timestamp="2026-05-06T14:32:00Z",
    )
    assert "[Scoopy]" in note
    assert "ghl_send_message" in note
    assert "2026-05-06T14:32:00Z" in note
    assert "Customer asked how to pay" in note
    assert "Approved by: liam" in note


def test_post_auto_note_calls_ghl_client():
    fake_client = MagicMock()
    fake_client.post.return_value = MagicMock(status_code=200, json=lambda: {"id": "n1"})
    post_auto_note(
        client=fake_client,
        contact_id="c1",
        action_name="ghl_remove_tag",
        reason="task complete",
        approver="liam",
        result="success",
    )
    fake_client.post.assert_called_once()
    args, kwargs = fake_client.post.call_args
    # Implementation calls client.post(path, payload=...). Be flexible about positional vs keyword.
    path = args[0] if args else kwargs.get("path")
    payload = kwargs.get("payload") or (args[1] if len(args) > 1 else None)
    assert path == "/contacts/c1/notes"
    assert "[Scoopy] ghl_remove_tag" in payload["body"]
