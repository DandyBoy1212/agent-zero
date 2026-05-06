### ghl_list_watching_contacts:
List all contacts that have the `scoopy-watching` tag — i.e., all customers with active Scoopy tasks. Optionally includes each contact's open `[REPLY]` and `[ACTION]` tasks. Use this when the operator asks broad questions like "what's outstanding?" or "show me all customer tasks Scoopy is watching."

**args:**
- include_tasks: bool, default true — if true, fetch each contact's open Scoopy tasks too (slower but more useful). If false, just list contacts.
- tag: string, default "scoopy-watching" — override only if asked about a non-default trigger tag.

**usage:**
~~~json
{
    "thoughts": ["Operator asked for outstanding tasks; list all watching contacts and their tasks"],
    "tool_name": "ghl_list_watching_contacts",
    "tool_args": {"include_tasks": true}
}
~~~
