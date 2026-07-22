### think_harder:
Switch to the high end model for the rest of this turn, because this problem is worth being right about. You run on the everyday model by default, which is fast and cheap and fine for most of what you are asked.

Call this BEFORE you start working on the hard part, not after you have already answered. It changes the model doing the rest of this turn, so calling it at the end achieves nothing.

It lasts for this turn only. Afterwards you go back to the everyday model automatically, so do not assume you are still on it in your next reply.

**Use it when:**
- You are about to queue anything through notify_owner that moves money, changes a price, or cancels a service
- A customer's message is ambiguous and guessing wrong would send the wrong thing to a real person
- You are reconciling numbers, dates or billing cadence and the arithmetic has to be right
- Liam or a staff member asks you to think carefully, take your time, or double check

**Do not use it for:**
- Looking something up, checking today's worklist, or reading a contact
- Small talk, or answering a question you already know the answer to
- Every turn "just in case". It costs roughly five times as much per turn, and using it everywhere is the same as not having it

**args:**
- reason: one line on why this one is worth it (required)

**usage:**
~~~json
{
    "thoughts": ["This is a refund on a live invoice; wrong number means real money out. Stepping up before I draft it."],
    "tool_name": "think_harder",
    "tool_args": {
        "reason": "refund amount on a live invoice, must be exact"
    }
}
~~~
