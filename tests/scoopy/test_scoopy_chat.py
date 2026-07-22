"""The no-key / wrong-key / unconfigured-env matrix for ScoopyChat and
ScoopyChatPoll is covered by the parametrized _handlers() list in
test_api_auth.py, which both classes were added to. What's left here is the
regression guard specific to these two: the in-body check_relay_key call,
which must never be quietly dropped by a future "cleanup" -- the (now
fixed) gap this closes is that the guard used to inspect ScoopyChat only,
so removing the gate from ScoopyChatPoll alone still passed."""

import inspect


def test_chat_creates_contexts_with_the_scoopy_profile(monkeypatch):
    """The live smoke test on 2026-07-21 got 'I'm Agent Zero, your AI
    assistant' back, because use_context builds every context with a bare
    initialize_agent() and no profile."""
    import scoopy_chat

    captured = {}

    def _fake_initialize_agent(override_settings=None):
        captured["override"] = override_settings
        return object()

    monkeypatch.setattr(scoopy_chat, "initialize_agent", _fake_initialize_agent)

    scoopy_chat.build_scoopy_config()

    assert captured["override"] == {"agent_profile": "scoopy"}


def test_chat_does_not_reintroduce_the_open_endpoint_pattern():
    """The framework flags stay False because the gate reads the
    environment rather than settings.json, which is wiped on restart. The
    protection must therefore be in the body. This test exists so nobody
    later 'tidies up' by deleting the in-body check, for either handler."""
    from scoopy_chat import ScoopyChat
    from scoopy_chat_poll import ScoopyChatPoll

    for handler_cls in (ScoopyChat, ScoopyChatPoll):
        source = inspect.getsource(handler_cls)
        assert "check_relay_key" in source, (
            f"{handler_cls.__name__} lost its in-body relay-key gate"
        )
