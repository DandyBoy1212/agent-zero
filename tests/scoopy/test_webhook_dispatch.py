import json
from unittest.mock import MagicMock
import pytest
from webhook_dispatch import (
    verify_signature, extract_contact_id, find_matching_reply_tasks,
    build_synthetic_prompt,
)


def test_verify_signature_test_mode(monkeypatch):
    monkeypatch.setenv("WEBHOOK_TEST_MODE", "1")
    assert verify_signature(b"any", None) is True


def test_verify_signature_real_mode_rejects_when_no_secret(monkeypatch):
    monkeypatch.delenv("WEBHOOK_TEST_MODE", raising=False)
    monkeypatch.setenv("GHL_WEBHOOK_SECRET", "")
    assert verify_signature(b"any", "abc") is False


def test_verify_signature_real_mode_validates_hmac(monkeypatch):
    import hmac, hashlib
    monkeypatch.delenv("WEBHOOK_TEST_MODE", raising=False)
    monkeypatch.setenv("GHL_WEBHOOK_SECRET", "shh")
    body = b'{"hello": 1}'
    good = hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, good) is True
    assert verify_signature(body, "wrong") is False


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
