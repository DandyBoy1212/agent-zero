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
