### mem0_save_candidate:
Queue a fact for owner approval before persisting to Mem0. Use when you encounter a fact worth remembering for future interactions (preferences, dog quirks, policy clarification, etc.). DOES NOT save directly — owner approves via inbox; persists with provenance.

**args:**
- contact_id: GHL contact id (required, even for business: namespace — used to route the curation card)
- namespace: contact:{id} | business:scoop_patrol | procedures:scoop_patrol | staff:{email} (required)
- fact: the thing worth remembering, in plain English (required)
- why_save: one-line why this is worth remembering (required)
- taught_by: the email from the `[staff: ...]` line, or "unknown" if there is no such line (required)

`taught_by` is who SAID it. It is stored separately from who approved it, because
those are usually different people and a shared memory nobody can trace is a
shared memory nobody can correct.

**usage:**
~~~json
{
    "thoughts": ["Mrs Jenkins mentioned she prefers WhatsApp; worth remembering"],
    "tool_name": "mem0_save_candidate",
    "tool_args": {
        "contact_id": "abc123",
        "namespace": "contact:abc123",
        "fact": "Mrs Jenkins prefers WhatsApp over SMS for payment reminders",
        "why_save": "stated preference; impacts how we contact her in future"
    }
}
~~~
