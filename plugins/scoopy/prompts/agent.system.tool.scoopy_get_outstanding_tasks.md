### scoopy_get_outstanding_tasks:
Returns ALL outstanding tasks assigned to you, regardless of due date. Use when the operator asks broad "what's outstanding" / "show me everything I'm watching" questions.

Returns three lists: reply (all open [REPLY]), action (all open [ACTION] regardless of due date), other (open tasks without a recognised prefix).

Reads from the Firestore task cache (sub-second). Cache is the source of truth; do NOT fall back to iterating contacts.

**args:** none

**usage:**
~~~json
{
    "thoughts": ["Operator asked for the full outstanding list"],
    "tool_name": "scoopy_get_outstanding_tasks",
    "tool_args": {}
}
~~~
