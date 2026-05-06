### ghl_get_tasks_for_contact:
List a contact's open tasks, optionally filtered. Useful to check if a follow-up is already scheduled before creating a new one.

**args:**
- contact_id: GHL contact id (required)
- assigned_to_scoopy_only: if true, only tasks assigned to Scoopy (default false)
- title_prefix: e.g. "[REPLY]" or "[ACTION]" (optional)

**usage:**
~~~json
{
    "thoughts": ["Check if there's already an open follow-up task before creating another one"],
    "tool_name": "ghl_get_tasks_for_contact",
    "tool_args": {"contact_id": "abc123", "assigned_to_scoopy_only": true}
}
~~~
