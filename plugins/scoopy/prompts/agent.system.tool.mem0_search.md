### mem0_search:
Search Scoopy's memory before drafting any reply. Three namespaces:
- contact:{ghl_contact_id} — per-customer episodic (last interactions, preferences, dog quirks)
- business:scoop_patrol — global policies, pricing rules, never-do's
- procedures:scoop_patrol — global how-tos (cancellation flow, payment chase)

Always search BOTH a contact namespace and the business namespace before drafting.

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
