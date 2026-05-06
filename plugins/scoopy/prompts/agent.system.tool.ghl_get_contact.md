### ghl_get_contact:
Fetch full details for a known contact by id. Returns custom fields, tags, basic info.

**args:**
- contact_id: GHL contact id (required)

**usage:**
~~~json
{
    "thoughts": ["Need to check her current service status before drafting"],
    "tool_name": "ghl_get_contact",
    "tool_args": {"contact_id": "abc123"}
}
~~~
