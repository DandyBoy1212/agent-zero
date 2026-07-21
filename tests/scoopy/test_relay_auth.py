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


def test_non_ascii_provided_key_is_rejected_not_typeerror(monkeypatch):
    """A non-ASCII X-API-KEY must fail closed with RelayAuthError, not TypeError.

    hmac.compare_digest raises TypeError when comparing strings containing
    non-ASCII characters. Left unhandled, that would surface as an
    unhandled 500 instead of the clean 401 callers expect from
    `except RelayAuthError`.
    """
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    with pytest.raises(RelayAuthError):
        check_relay_key("café")


def test_matching_non_ascii_key_is_accepted(monkeypatch):
    """A legitimate non-ASCII key must still be accepted, not just blocked."""
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "café")
    assert check_relay_key("café") is None


def test_unencodable_provided_key_is_rejected_not_unicodeencodeerror(monkeypatch):
    """A provided key containing a lone surrogate must fail closed with
    RelayAuthError, not UnicodeEncodeError.

    WSGI/ASGI servers commonly decode raw header bytes with
    surrogateescape, so a header carrying invalid UTF-8 arrives as exactly
    this kind of string. str.encode("utf-8") raises UnicodeEncodeError on
    it, which would otherwise escape as an unhandled 500 instead of the
    clean 401 callers expect from `except RelayAuthError`.
    """
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    with pytest.raises(RelayAuthError):
        check_relay_key("\udc80abc")


def test_unencodable_configured_key_is_rejected_not_unicodeencodeerror(monkeypatch):
    """The mirror case: an unencodable configured key must also raise
    RelayAuthError rather than crashing, even against a well-formed
    provided key.
    """
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "\udc80abc")
    with pytest.raises(RelayAuthError):
        check_relay_key("anything")


class _NoEncode:
    """An object with no .encode method, e.g. a stray header value."""

    def __repr__(self):
        return "_NoEncode()"


@pytest.mark.parametrize(
    "provided",
    [
        b"wrong-key",
        ["a-key"],
        12345,
        _NoEncode(),
    ],
    ids=["bytes", "list", "int", "no-encode-object"],
)
def test_non_string_provided_key_is_rejected_not_attributeerror(monkeypatch, provided):
    """Any truthy non-string input must fail closed with RelayAuthError, not
    AttributeError.

    A repeated-header multidict can hand back a list, a misbehaving
    upstream can hand back bytes or an int, and none of these have
    `.encode` (bytes has `.decode` instead). Left unhandled, that would
    surface as an unhandled 500 instead of the clean 401 callers expect
    from `except RelayAuthError`. The guard must reject at the boundary
    based on type, not attempt-then-catch each failure mode individually.
    """
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "s3cret-key")
    with pytest.raises(RelayAuthError):
        check_relay_key(provided)
