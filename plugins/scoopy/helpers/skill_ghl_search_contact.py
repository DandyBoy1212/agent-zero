"""ghl_search_contact — find contacts by free-form query (name/phone/email).

Read-only skill. Used when the operator asks Scoopy to act on a customer
referenced by name, e.g. 'send Mrs Jenkins a message'.

Endpoint: POST https://services.leadconnectorhq.com/contacts/search
Body:     {"locationId": <env GHL_LOCATION_ID>, "query": <q>, "pageLimit": N}
Response: {"contacts": [...]}
"""
from __future__ import annotations
import os
from typing import Any
from scoopy_logging import log


def ghl_search_contact(*, client, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search Scoop Patrol's contacts by free-form query.

    Args:
        client: GhlClient instance
        query: free-form text to match against name/phone/email (fuzzy on GHL side)
        limit: max number of results to return (default 10)

    Returns:
        list of contact dicts. Each contact typically contains
        {id, firstName, lastName, contactName, email, phone, customFields, tags, ...}
    """
    log("skill_helper_call", name="ghl_search_contact", limit=limit)
    location_id = os.getenv("GHL_LOCATION_ID")
    results = client.search_contacts(query=query, location_id=location_id, limit=limit)
    log("skill_helper_result", name="ghl_search_contact", status="success", count=len(results))
    return results
