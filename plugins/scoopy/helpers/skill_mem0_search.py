"""mem0_search — read helper. No approval gate.

Returns up to `limit` memories from the given namespace. Used by the agent
before drafting any reply to pull episodic + semantic context.
"""
from __future__ import annotations
from typing import Any
from mem0_client import Mem0Client
from scoopy_logging import log


def mem0_search(
    *,
    namespace: str,
    query: str,
    limit: int = 5,
    client: Mem0Client | None = None,
) -> list[dict[str, Any]]:
    log("skill_helper_call", name="mem0_search", namespace=namespace)
    if not namespace:
        log("skill_helper_result", name="mem0_search", status="success", hits=0, reason="no_namespace")
        return []
    c = client or Mem0Client()
    results = c.search(namespace=namespace, query=query, limit=limit)
    log("skill_helper_result", name="mem0_search", status="success", hits=len(results))
    return results
