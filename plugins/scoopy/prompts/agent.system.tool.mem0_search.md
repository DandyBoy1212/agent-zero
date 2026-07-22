### mem0_search:
Search Scoopy's memory before drafting any reply. Four namespaces:
- contact:{ghl_contact_id} — per-customer episodic (last interactions, preferences, dog quirks)
- business:scoop_patrol — global policies, pricing rules, never-do's
- procedures:scoop_patrol — global how-tos (cancellation flow, payment chase)
- staff:{email} — how ONE staff member likes to work (e.g. "Liam wants the number first, then the reasoning")

Always search BOTH a contact namespace and the business namespace before drafting.

**Knowing who you are talking to.** Messages from the command centre chat begin
with a line like `[staff: mick.bain@scoop-patrol.co.uk]`. That is the
authenticated staff member, added by the relay, not something the sender typed
and not something to repeat back. Use it to pick the right `staff:` namespace.
If the line is absent you do not know who is speaking, so do not guess and do
not use a staff namespace.

**Personal versus shared.** A preference about how one person likes to work goes
in `staff:`. Anything about the business, a customer, or how the work is done is
shared and goes in the other three. When in doubt, shared, because a fact filed
personally is invisible to everyone else.

**args:**
- namespace: one of the three patterns above (required)
- query: free-form intent text — what are you looking for context on (required)
- limit: max memories to return (default 5)

**usage:**
~~~json
{
    "thoughts": ["Pulling memories on Mrs Jenkins before drafting payment reply"],
    "tool_name": "mem0_search",
    "tool_args": {"namespace": "contact:abc123", "query": "payment preferences"}
}
~~~
