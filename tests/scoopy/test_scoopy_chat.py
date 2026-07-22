"""The no-key / wrong-key / unconfigured-env matrix for ScoopyChat and
ScoopyChatPoll is covered by the parametrized _handlers() list in
test_api_auth.py, which both classes were added to. What's left here is the
regression guard specific to these two: the in-body check_relay_key call,
which must never be quietly dropped by a future "cleanup" -- the (now
fixed) gap this closes is that the guard used to inspect ScoopyChat only,
so removing the gate from ScoopyChatPoll alone still passed."""

import asyncio
import inspect
import threading

import pytest
from flask import Flask


class _JsonReq:
    """Minimal JSON request stand-in. Only carries what ScoopyChat.process
    actually reads before delegating to the parent: auth header and a
    `context` id in the JSON body."""

    def __init__(self, headers=None, context_id=""):
        self.headers = headers or {}
        self.args = {}
        self.form = {}
        self.content_type = "application/json"
        self.is_json = True
        self._context_id = context_id

    def get_json(self, silent=False):
        return {"context": self._context_id}


def _build(handler_cls):
    return handler_cls(Flask(__name__), threading.Lock())


def _run(handler, request):
    return asyncio.run(handler.process({}, request))


@pytest.fixture
def relay_key(monkeypatch):
    monkeypatch.setenv("SCOOPY_RELAY_KEY", "test-key")
    return "test-key"


def test_process_creates_a_context_with_the_scoopy_profile(monkeypatch, relay_key):
    """Replaces test_chat_creates_contexts_with_the_scoopy_profile, deleted
    because it only proved build_scoopy_config() builds a config object --
    never that process() does anything with it. The gap that left open was
    closed (or so it seemed) by a live smoke test that asked the running
    agent "who are you?" and read the reply; that reply is
    prompts/fw.initial_message.md:11, a hardcoded greeting rendered on
    every context creation regardless of profile, so it could never have
    caught a regression here.

    This test instead drives ScoopyChat.process() end to end and inspects
    the actual AgentContext it left behind, the way the running server
    would use it on the next turn.
    """
    from agent import AgentConfig, AgentContext
    import api.message_async as message_async_module
    from scoopy_chat import ScoopyChat

    async def _noop_process(self, input, request):
        return {"message": "stubbed", "context": ""}

    # ScoopyChat inherits MessageAsync -> Message -> ApiHandler. MessageAsync
    # itself only overrides respond(), so super().process() in
    # ScoopyChat.process actually resolves to Message.process, which would
    # run the full agent message loop. Patch it out at the MessageAsync
    # level (the class super() is called against) so it's a no-op instead.
    monkeypatch.setattr(message_async_module.MessageAsync, "process", _noop_process)
    monkeypatch.setattr(
        "scoopy_chat.initialize_agent",
        lambda override_settings=None: AgentConfig(
            profile="scoopy", mcp_servers='{"mcpServers": {}}'
        ),
    )

    ctxid = "pytest-scoopy-chat-creates-context"
    assert AgentContext.get(ctxid) is None  # guard against id reuse across runs
    try:
        req = _JsonReq({"X-API-KEY": relay_key}, context_id=ctxid)
        _run(_build(ScoopyChat), req)

        created = AgentContext.get(ctxid)
        assert created is not None
        assert created.config.profile == "scoopy"
    finally:
        AgentContext.remove(ctxid)


def test_process_does_not_replace_an_existing_context(monkeypatch, relay_key):
    """The fix only creates into emptiness (`AgentContext.get(ctxid) is
    None`). Prove that guard is load-bearing: a context that already
    exists on this id, on some other profile, must come out untouched --
    overwriting it would silently drop a live conversation's history and
    agent state on every subsequent turn.
    """
    from agent import AgentConfig, AgentContext
    import api.message_async as message_async_module
    from scoopy_chat import ScoopyChat

    async def _noop_process(self, input, request):
        return {"message": "stubbed", "context": ""}

    def _fail_if_called(override_settings=None):
        raise AssertionError(
            "build_scoopy_config() should not run when a context already "
            "exists for this id"
        )

    monkeypatch.setattr(message_async_module.MessageAsync, "process", _noop_process)
    monkeypatch.setattr("scoopy_chat.initialize_agent", _fail_if_called)

    ctxid = "pytest-scoopy-chat-preserves-context"
    assert AgentContext.get(ctxid) is None  # guard against id reuse across runs
    existing = AgentContext(
        config=AgentConfig(profile="agent0", mcp_servers='{"mcpServers": {}}'),
        id=ctxid,
        set_current=False,
    )
    try:
        req = _JsonReq({"X-API-KEY": relay_key}, context_id=ctxid)
        _run(_build(ScoopyChat), req)

        after = AgentContext.get(ctxid)
        assert after is existing
        assert after.config.profile == "agent0"
    finally:
        AgentContext.remove(ctxid)


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
