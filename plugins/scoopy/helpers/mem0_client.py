"""Thin wrapper around Mem0 hosted SDK.

Wraps mem0ai's MemoryClient with a small surface area used by Scoopy:
- search(namespace, query, limit) -> list[dict]
- add(namespace, fact, metadata) -> dict

We treat Mem0's `user_id` parameter as our namespace (contact:{id},
business:scoop_patrol, procedures:scoop_patrol).
"""
from __future__ import annotations
import os
from typing import Any

try:
    from mem0 import MemoryClient
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    MemoryClient = None  # type: ignore[assignment,misc]


class Mem0Client:
    """Thin wrapper around mem0ai.MemoryClient."""

    def __init__(self, api_key: str | None = None, client: Any = None):
        # Allow explicit client injection for tests
        if client is not None:
            self._client = client
            self.api_key = api_key
            return
        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        if not self.api_key:
            raise RuntimeError("MEM0_API_KEY not set")
        if not _SDK_AVAILABLE:
            raise RuntimeError("mem0ai SDK not installed; pip install mem0ai")
        self._client = MemoryClient(api_key=self.api_key)

    def search(self, *, namespace: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not namespace:
            return []
        results = self._client.search(query=query, user_id=namespace, limit=limit)
        # Normalize: SDK may return list-of-dicts directly OR {"results": [...]}
        if isinstance(results, dict):
            results = results.get("results") or results.get("memories") or []
        if not results:
            return []
        return list(results)[:limit]

    def add(
        self,
        *,
        namespace: str,
        fact: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._client.add(
            messages=[{"role": "user", "content": fact}],
            user_id=namespace,
            metadata=metadata or {},
        )
