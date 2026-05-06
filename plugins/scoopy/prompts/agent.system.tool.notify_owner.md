### notify_owner:
Queue an approval card for the owner (Liam). This is your ONLY path to write actions — sending messages, updating contacts, creating tasks, removing tags, persisting memory. You CANNOT write directly. Always call notify_owner; the dispatcher runs the queued actions only after the owner approves in the inbox.

**args:**
- contact_id: GHL contact id (required)
- draft: human-readable draft of what will be sent or done (required)
- reasoning: one-line why (required)
- action_type: one of in_scope | drift | escalation | create_task | memory_candidate (required)
- pending_actions: list of actions to run on approve, e.g. [{"skill": "ghl_send_message", "args": {"contact_id":"c1","message":"..."}}] (required)

**usage:**
~~~json
{
    "thoughts": ["Customer asked how to pay; in scope of [REPLY] task; sending Stripe link"],
    "tool_name": "notify_owner",
    "tool_args": {
        "contact_id": "abc123",
        "draft": "Hi Sarah! Easiest is the link below — tap to pay your invoice in seconds. Always on Doody, Scoopy 🐾",
        "reasoning": "in scope: customer asked how to pay; sending invoice link",
        "action_type": "in_scope",
        "pending_actions": [
            {"skill": "ghl_send_message", "args": {"contact_id": "abc123", "message": "Hi Sarah! ..."}}
        ]
    }
}
~~~
