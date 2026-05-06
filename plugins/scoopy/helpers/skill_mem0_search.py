"""mem0_search — read helper. No approval gate.

Returns up to `limit` memories from the given namespace. Used by the agent
before drafting any reply to pull episodic + semantic context.
"""
from __future__ import annotations
from typing import Any
from mem0_client import Mem0Client


def mem0_search(
    *,
    namespace: str,
    query: str,
    limit: int = 5,
    client: Mem0Client | None = None,
) -> list[dict[str, Any]]:
    if not namespace:
        return []
    c = client or Mem0Client()
    return c.search(namespace=namespace, query=query, limit=limit)
