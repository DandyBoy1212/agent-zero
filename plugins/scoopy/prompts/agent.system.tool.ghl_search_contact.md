### ghl_search_contact:
Find contacts by free-form query (name, phone fragment, email). Use when the operator references a customer by name. Returns a list of contacts; pick the right one by context, then act on its id.

**args:**
- query: free-form text to match against name/phone/email (required)
- limit: max results (default 10)

**usage:**
~~~json
{
    "thoughts": ["Operator said 'send Mrs Jenkins a message'; need to find her contact id"],
    "tool_name": "ghl_search_contact",
    "tool_args": {"query": "Mrs Jenkins"}
}
~~~
