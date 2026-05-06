### scoopy_get_tasks_for_today:
Your daily worklist. Returns the tasks you should work on today, split by type:
- reply: open [REPLY] tasks waiting on customer replies — for visibility, not direct action (the inbound-message webhook will wake you when a reply actually arrives)
- action_due: open [ACTION] tasks with due_date on or before today — work through these one by one, drafting via notify_owner

Reads from the Firestore task cache (synced live from GHL via the task webhook). Sub-second; do NOT iterate contacts to find tasks.

Use this when:
- Starting a daily work session
- The operator asks "what do you have to do today" / "what's on your plate"
- The cron sweep wakes you for the daily ACTION processing

**args:** none

**usage:**
~~~json
{
    "thoughts": ["Operator asked what's on my plate today — checking the cached worklist"],
    "tool_name": "scoopy_get_tasks_for_today",
    "tool_args": {}
}
~~~
