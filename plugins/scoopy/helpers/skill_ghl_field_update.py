"""ghl_field_update skill: update one or more custom fields on a GHL contact.

GHL API format (verified against execution/patch_wednesday_nsd.py):
    PUT /contacts/{contact_id}
    body: {"customFields": [{"id": <field_id>, "value": <value>}, ...]}

Accepts both bare field NAMES (mapped via _FIELD_NAME_TO_ID below) and raw
GHL custom-field IDs. Field IDs are 24-character alphanumeric strings — any
key in `field_updates` not present in the name map is treated as a raw ID
and passed through verbatim.

Seed map sourced from all_fields_master.txt (the agentic-workflows-skill
codebase). Add additional names here as we hit them.

Approval-gated: only called by execute_with_approval after a valid token is consumed.
"""
from __future__ import annotations
from typing import Any
from auto_note import post_auto_note


# Seed map: human-readable name -> GHL custom field ID.
# Source: agentic-workflows-skill/all_fields_master.txt
# TODO: expand as new field names are needed by directives. Keep names
# snake_case. If a directive uses a name not in this map, the agent can
# pass the raw 24-char field ID instead.
_FIELD_NAME_TO_ID: dict[str, str] = {
    # Note: there is no "service_status" custom field in the live tenant —
    # service state is tracked via tags + Payment Status. Keeping the key
    # commented for discoverability.
    # "service_status": "<no field id>",
    "payment_status": "Vgj52YBcgzxd1jBGmJK1",
    "next_service_date": "BEkIldTfzjiLn7DXj2Io",
    "payment_frequency": "O85OWL87X1fWC77BhTd2",
    "service_day": "LN8ljDGEpB8cfLmnt8vz",
    "garden_size": "xMN7bGxjpJ1I8Z8gq678",
}


def _resolve_field_id(key: str) -> str:
    """Map a name to ID, or pass through if it already looks like an ID."""
    return _FIELD_NAME_TO_ID.get(key, key)


def ghl_field_update(
    *,
    client,
    contact_id: str,
    field_updates: dict[str, Any],
    reasoning: str,
    approver: str,
) -> dict[str, Any]:
    custom_fields = [
        {"id": _resolve_field_id(k), "value": v}
        for k, v in field_updates.items()
    ]
    payload = {"customFields": custom_fields}
    resp = client.put(f"/contacts/{contact_id}", payload=payload)
    summary = "Updated fields: " + ", ".join(f"{k}={v}" for k, v in field_updates.items())
    if resp.status_code in (200, 201):
        post_auto_note(
            client=client,
            contact_id=contact_id,
            action_name="ghl_field_update",
            reason=reasoning,
            approver=approver,
            result=f"success: {len(custom_fields)} field(s) updated",
            payload_summary=summary,
        )
        return {"status": "success", "updates": field_updates}
    post_auto_note(
        client=client,
        contact_id=contact_id,
        action_name="ghl_field_update",
        reason=reasoning,
        approver=approver,
        result=f"error: status={resp.status_code}",
        payload_summary=summary,
    )
    return {"status": "error", "code": resp.status_code, "body": resp.text}
