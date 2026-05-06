"""In-memory approval-token store.

Tokens are single-use, TTL-bounded. Process-local storage for v0; for
multi-instance deploys, swap to Mem0 / Redis / Firestore.

This is the gatekeeper between an agent's `notify_owner` call (which queues
a card) and `execute_with_approval` (which runs the underlying skill). A
token is issued only when notify_owner succeeds, and consumed only when the
owner clicks Approve in the inbox.
"""
from __future__ import annotations
import secrets
import time
from typing import Any


class ApprovalError(Exception):
    """Raised when a token is unknown, expired, or already consumed."""


class ApprovalStore:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._items: dict[str, tuple[float, Any]] = {}

    def issue(self, card: Any) -> str:
        token = secrets.token_urlsafe(24)
        self._items[token] = (time.time(), card)
        return token

    def consume(self, token: str) -> Any:
        item = self._items.pop(token, None)
        if item is None:
            raise ApprovalError("unknown token")
        issued_at, card = item
        if time.time() - issued_at > self.ttl:
            raise ApprovalError("token expired")
        return card

    def list_pending(self) -> list[tuple[str, Any]]:
        now = time.time()
        return [(t, c) for t, (issued, c) in self._items.items() if now - issued <= self.ttl]


# Module-level singleton for the running service.
default_store = ApprovalStore(ttl_seconds=3600)
