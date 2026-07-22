"""In-memory approval-token store.

Tokens are single-use, TTL-bounded. Process-local storage for v0; for
multi-instance deploys, swap to Mem0 / Redis / Firestore.

This is the gatekeeper between an agent's `notify_owner` call (which queues
a card) and `execute_with_approval` (which runs the underlying skill). A
token is issued only when notify_owner succeeds, and consumed only when the
owner clicks Approve in the inbox.
"""
from __future__ import annotations
import json
import os
import secrets
import time
from typing import Any
from scoopy_logging import log


class ApprovalError(Exception):
    """Raised when a token is unknown, expired, or already consumed."""


class ApprovalStore:
    """Pending approval cards.

    Persists to JSON when given a path. Scoopy restarts on every deploy and
    every environment change, and a card is meant to be answerable hours after
    it was raised. Held only in memory, a card raised overnight is gone by
    morning with no trace and no notice to whoever was going to approve it.

    Writes the whole file on every change. The store holds a handful of cards
    at a time, so this is simpler than incremental updates and has no partial
    write to reason about.
    """

    def __init__(self, ttl_seconds: int = 3600, path: str | None = None):
        self.ttl = ttl_seconds
        self.path = path
        self._items: dict[str, tuple[float, Any]] = {}
        if path:
            self._load()

    def _load(self) -> None:
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._items = {
                token: (float(entry["issued_at"]), entry["card"])
                for token, entry in raw.items()
            }
        except Exception as e:
            # Fail toward an empty store, never toward a crash loop. A
            # malformed file must not stop Scoopy booting; losing pending
            # cards is bad, a container that will not start is worse.
            log("approval_store_load_failed", error=f"{type(e).__name__}: {e}")
            self._items = {}

    def _save(self) -> None:
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            payload = {
                token: {"issued_at": issued, "card": card}
                for token, (issued, card) in self._items.items()
            }
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except Exception as e:
            log("approval_store_save_failed", error=f"{type(e).__name__}: {e}")

    def issue(self, card: Any) -> str:
        token = secrets.token_urlsafe(24)
        self._items[token] = (time.time(), card)
        self._save()
        log("approval_issued", token_prefix=token[:6])
        return token

    def consume(self, token: str) -> Any:
        item = self._items.pop(token, None)
        if item is None:
            raise ApprovalError("unknown token")
        self._save()
        issued_at, card = item
        if time.time() - issued_at > self.ttl:
            raise ApprovalError("token expired")
        return card

    def list_pending(self) -> list[tuple[str, Any]]:
        now = time.time()
        return [(t, c) for t, (issued, c) in self._items.items() if now - issued <= self.ttl]


# Module-level singleton for the running service.
# usr/ is the persistent disk mount on Render, so this survives restarts.
default_store = ApprovalStore(
    ttl_seconds=3600,
    path=os.path.join("usr", "scoopy_approvals.json"),
)
