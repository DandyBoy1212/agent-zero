"""Thin GHL HTTP client used by Scoopy skills.

Reuses the convention from execution/create_scheduled_invoice.py
(same base URL, same auth headers).
"""
from __future__ import annotations
import os
import httpx
from typing import Any

BASE_URL = "https://services.leadconnectorhq.com"


class GhlClient:
    def __init__(self, api_key: str | None = None, location_id: str | None = None):
        self.api_key = api_key or os.getenv("SCOOPY_GHL_API_KEY") or os.getenv("GHL_API_KEY")
        self.location_id = location_id or os.getenv("GHL_LOCATION_ID")
        if not self.api_key:
            raise RuntimeError("Missing SCOOPY_GHL_API_KEY (or GHL_API_KEY)")
        self._client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_contact(self, contact_id: str) -> dict[str, Any]:
        resp = self._client.get(f"{BASE_URL}/contacts/{contact_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_tasks_for_contact(self, contact_id: str) -> list[dict[str, Any]]:
        resp = self._client.get(f"{BASE_URL}/contacts/{contact_id}/tasks", headers=self._headers())
        resp.raise_for_status()
        return resp.json().get("tasks", [])

    def search_contacts(
        self, *, query: str, location_id: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """POST /contacts/search — fuzzy match on name/phone/email.

        Body shape per GHL API (verified via working execution scripts):
            {"locationId": "...", "query": "...", "pageLimit": N}
        Returns the `contacts` array from the response (or [] if missing).
        """
        payload = {
            "locationId": location_id or self.location_id,
            "query": query,
            "pageLimit": limit,
        }
        resp = self._client.post(
            f"{BASE_URL}/contacts/search", headers=self._headers(), json=payload
        )
        resp.raise_for_status()
        return resp.json().get("contacts", [])

    def search_contacts_by_tag(
        self,
        *,
        tag: str,
        location_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """POST /contacts/search — filter contacts by tag.

        Tries the documented `filters` array shape first (per GHL "advanced
        search" docs: field=tags, operator=contains, value=<tag>). If that
        returns nothing, falls back to a free-form query on the tag name —
        GHL's text search will sometimes match tag strings, which is good
        enough for a small location. Always returns a list (possibly empty).
        """
        loc = location_id or self.location_id

        # Primary: filters array — SearchBodyV2DTO is schema-less in the spec
        # but the documented advanced-search shape is filters[{field,operator,value}].
        filter_payload = {
            "locationId": loc,
            "pageLimit": limit,
            "filters": [
                {"field": "tags", "operator": "contains", "value": tag}
            ],
        }
        try:
            resp = self._client.post(
                f"{BASE_URL}/contacts/search",
                headers=self._headers(),
                json=filter_payload,
            )
            resp.raise_for_status()
            contacts = resp.json().get("contacts", [])
        except Exception:
            contacts = []

        if contacts:
            # Defence in depth: GHL "contains" can be permissive; require the
            # tag to actually be present on each returned contact.
            return [c for c in contacts if tag in (c.get("tags") or [])]

        # Fallback: query-based search, then filter in-process by exact tag.
        try:
            query_contacts = self.search_contacts(
                query=tag, location_id=loc, limit=limit
            )
        except Exception:
            query_contacts = []
        return [c for c in query_contacts if tag in (c.get("tags") or [])]

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        resp = self._client.get(f"{BASE_URL}/conversations/{conversation_id}/messages", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        return self._client.post(f"{BASE_URL}{path}", headers=self._headers(), json=payload)

    def delete(self, path: str, payload: dict[str, Any] | None = None) -> httpx.Response:
        return self._client.request("DELETE", f"{BASE_URL}{path}", headers=self._headers(), json=payload)

    def patch(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        return self._client.patch(f"{BASE_URL}{path}", headers=self._headers(), json=payload)

    def put(self, path: str, payload: dict[str, Any]) -> httpx.Response:
        return self._client.put(f"{BASE_URL}{path}", headers=self._headers(), json=payload)
