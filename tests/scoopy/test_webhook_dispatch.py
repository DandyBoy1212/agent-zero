import json
from unittest.mock import MagicMock
import pytest
from webhook_dispatch import (
    verify_signature, extract_contact_id, find_matching_reply_tasks,
    build_synthetic_prompt, extract_message,
)
from webhook_dispatch import extract_signature


def test_extract_signature_reads_ghl_header():
    assert extract_signature({"x-ghl-signature": "abc"}) == "abc"


def test_extract_signature_reads_wh_header():
    """GHL's documented header name. Which one it really sends is untested
    against production, so both are accepted."""
    assert extract_signature({"x-wh-signature": "abc"}) == "abc"


def test_extract_signature_is_case_insensitive():
    assert extract_signature({"X-WH-Signature": "abc"}) == "abc"


def test_extract_signature_returns_none_when_absent():
    assert extract_signature({"content-type": "application/json"}) is None


def test_test_mode_bypass_still_works_for_local_runs(monkeypatch):
    monkeypatch.setenv("WEBHOOK_TEST_MODE", "1")
    assert verify_signature(b"body", None) is True


def test_bypass_is_off_by_default(monkeypatch):
    monkeypatch.delenv("WEBHOOK_TEST_MODE", raising=False)
    assert verify_signature(b"body", None) is False


def test_verify_signature_test_mode(monkeypatch):
    monkeypatch.setenv("WEBHOOK_TEST_MODE", "1")
    assert verify_signature(b"any", None) is True


def test_verify_signature_rejects_when_no_signature_header(monkeypatch):
    monkeypatch.delenv("WEBHOOK_TEST_MODE", raising=False)
    assert verify_signature(b'{"hello": 1}', None) is False
    assert verify_signature(b'{"hello": 1}', "") is False


def test_verify_signature_rejects_invalid_signature(monkeypatch):
    import base64
    monkeypatch.delenv("WEBHOOK_TEST_MODE", raising=False)
    body = b'{"hello": 1}'
    # Random 256-byte blob, base64 encoded — valid format, wrong signature
    bogus = base64.b64encode(b"\x00" * 256).decode()
    assert verify_signature(body, bogus) is False
    # Total garbage that isn't even valid base64
    assert verify_signature(body, "not-base64-!!!") is False


def test_verify_signature_accepts_valid_rsa_signature(monkeypatch):
    """Generate a test keypair, monkey-patch the embedded public key, and
    sign a body with the matching private key — confirms the verify path
    actually validates a good signature."""
    import base64
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as _pad
    from cryptography.hazmat.primitives import hashes as _hashes, serialization as _ser
    import webhook_dispatch as wd

    monkeypatch.delenv("WEBHOOK_TEST_MODE", raising=False)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=_ser.Encoding.PEM,
        format=_ser.PublicFormat.SubjectPublicKeyInfo,
    )
    monkeypatch.setattr(wd, "GHL_PUBLIC_KEY_PEM", public_pem)

    body = b'{"hello": 1}'
    sig = private_key.sign(body, _pad.PKCS1v15(), _hashes.SHA256())
    sig_b64 = base64.b64encode(sig).decode()
    assert wd.verify_signature(body, sig_b64) is True
    # Tampered body must fail
    assert wd.verify_signature(b'{"hello": 2}', sig_b64) is False


def test_extract_contact_id_flat():
    assert extract_contact_id({"contact_id": "c1"}) == "c1"
    assert extract_contact_id({"contactId": "c2"}) == "c2"


def test_extract_contact_id_nested():
    assert extract_contact_id({"contact": {"id": "c3"}}) == "c3"


def test_extract_contact_id_n8n_string_body():
    inner = {"contactId": "c4"}
    assert extract_contact_id({"body": json.dumps(inner)}) == "c4"


def test_extract_contact_id_missing():
    assert extract_contact_id({}) is None


def test_find_matching_reply_tasks_filters(monkeypatch):
    monkeypatch.setenv("SCOOPY_USER_ID", "scoopy-id")
    client = MagicMock()
    client.get_tasks_for_contact.return_value = [
        {"id": "t1", "title": "[REPLY] x", "assignedTo": "scoopy-id", "completed": False},
        {"id": "t2", "title": "[ACTION] y", "assignedTo": "scoopy-id", "completed": False},
        {"id": "t3", "title": "[REPLY] z", "assignedTo": "liam-id", "completed": False},
    ]
    res = find_matching_reply_tasks(client=client, contact_id="c1")
    assert len(res) == 1 and res[0]["id"] == "t1"


def test_build_synthetic_prompt_includes_essentials():
    tasks = [{"id": "t1", "title": "[REPLY] follow up payment", "body": "if asks how, send link"}]
    prompt = build_synthetic_prompt(
        contact_id="c1",
        tasks=tasks,
        message={"body": "How can I pay?"},
        contact={"contact": {"firstName": "Sarah", "lastName": "Jenkins"}},
    )
    assert "c1" in prompt
    assert "Sarah Jenkins" in prompt
    assert "How can I pay?" in prompt
    assert "[REPLY] follow up payment" in prompt
    assert "notify_owner" in prompt


def test_extract_message_flat_payload():
    payload = {
        "contactId": "c1",
        "body": "Hello scoopy",
        "messageType": "SMS",
        "direction": "inbound",
        "conversationId": "conv1",
    }
    msg = extract_message(payload)
    assert msg["body"] == "Hello scoopy"
    assert msg["messageType"] == "SMS"
    assert msg["direction"] == "inbound"
    assert msg["conversationId"] == "conv1"


def test_extract_message_nested_payload():
    payload = {
        "contactId": "c1",
        "message": {"body": "hi", "type": "SMS", "direction": "inbound"},
    }
    msg = extract_message(payload)
    assert msg["body"] == "hi"
    assert msg["messageType"] == "SMS"


def test_extract_message_n8n_string_body():
    import json
    inner = {"contactId": "c1", "body": "hello", "messageType": "Email"}
    payload = {"body": json.dumps(inner)}
    msg = extract_message(payload)
    assert msg["body"] == "hello"
    assert msg["messageType"] == "Email"


def test_extract_message_missing_returns_empty_dict():
    msg = extract_message({"contactId": "c1"})
    assert msg["body"] is None


def test_task_endpoint_accepts_both_signature_header_spellings():
    """scoopy_webhook_task.py must resolve signatures the same way
    scoopy_webhook_message.py does — via the shared extract_signature
    helper — not a hardcoded single header name. Regression test for the
    two endpoints disagreeing on x-wh-signature vs x-ghl-signature."""
    import scoopy_webhook_task as task_endpoint

    assert task_endpoint.extract_signature is extract_signature
    assert task_endpoint.extract_signature({"x-wh-signature": "abc"}) == "abc"
    assert task_endpoint.extract_signature({"x-ghl-signature": "abc"}) == "abc"
