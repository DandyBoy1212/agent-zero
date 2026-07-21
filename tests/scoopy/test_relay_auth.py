import pytest
from relay_auth import RelayAuthError, check_relay_key


def test_missing_env_var_fails_closed(monkeypatch):
    monkeypatch.delenv("SCOOPY_RELAY_KEY", raising=False)
    with pytest.raises(RelayAuthError) as exc:
        check_relay_key("anything")
    assert "not configured" in str(exc.value)


def test_empty_env_var_fails_closed(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "")
    with pytest.raises(RelayAuthError):
        check_relay_key("anything")


def test_correct_key_passes(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    assert check_relay_key("s3cret-key") is None


def test_wrong_key_raises(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    with pytest.raises(RelayAuthError):
        check_relay_key("wrong")


def test_absent_header_raises(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    with pytest.raises(RelayAuthError):
        check_relay_key(None)


def test_prefix_of_valid_key_is_rejected(monkeypatch):
    """Guards against a comparison that stops at the shorter string."""
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    with pytest.raises(RelayAuthError):
        check_relay_key("s3cret")
