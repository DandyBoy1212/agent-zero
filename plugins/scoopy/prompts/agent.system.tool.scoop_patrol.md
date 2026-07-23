### scoop_patrol:
Query the Scoop Patrol automation server (the one brain for customers, billing, routes and conversations). Reads answer immediately. Writes NEVER run from this tool: queue them on a notify_owner card as an mcp_action (see below) and the dispatcher runs them after the owner approves.

**args:**
- tool: which server tool (required)
- arguments: object of that tool's arguments (see below)

**read tools (call directly):**
- server.health {} — which tools are live; call first if something 404s
- customers.state {contact_id} — everything about one customer: CRM, all billing rails with a duplication verdict, scheduling, routing. Can be SLOW; prefer customers.find for a quick lookup
- customers.find {field: value, ...} — search customers across indexed fields, e.g. {"postcode": "DD5"}
- routes.get {start, end} — routes and stops for a date window (YYYY-MM-DD)
- conversations.unread {limit} — unread inbound customer messages
- billing.preview {contact_id, changes} — read-only price and schedule plan; ALWAYS call before proposing billing.apply and show the result in the card draft

**write tools (owner approval only — queue via notify_owner):**
billing.apply, messages.send, service.lifecycle, service.change_day, customers.update_inert

**usage (read):**
~~~json
{
    "thoughts": ["What does the server know about her before I draft?"],
    "tool_name": "scoop_patrol",
    "tool_args": {"tool": "customers.find", "arguments": {"postcode": "DD5 3RT"}}
}
~~~

**usage (write — always through notify_owner):**
~~~json
{
    "thoughts": ["Preview says weekly to monthly moves her to £64.00/4-weekly; queue the change for approval"],
    "tool_name": "notify_owner",
    "tool_args": {
        "contact_id": "abc123",
        "action_type": "billing_change",
        "draft": "Switch Anne to Monthly billing. Preview: £64.00 per 4-weekly invoice, next invoice 2026-08-01, no catch-up needed.",
        "reasoning": "Customer asked to pay monthly",
        "pending_actions": [
            {"skill": "mcp_action", "args": {"tool": "billing.apply", "arguments": {"contact_id": "abc123", "changes": {"payment_frequency": "Monthly"}}}}
        ]
    }
}
~~~

messages.send needs {contact_id, message, inbound_seen_through} — inbound_seen_through is the ISO timestamp of the newest inbound you have read for that contact (from conversations.unread or the webhook); the server refuses the send if anything newer exists, so you never reply over an unread message.
