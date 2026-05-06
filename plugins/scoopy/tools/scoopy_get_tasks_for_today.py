"""scoopy_get_tasks_for_today Tool — agent's daily worklist.

Reads from the Firestore task cache (populated by the GHL task webhook).
Returns:
    - reply:      open [REPLY] tasks (visibility, no direct action)
    - action_due: open [ACTION] tasks due on or before today

Read-only. break_loop=False so the agent keeps reasoning after the read.
"""
from __future__ import annotations
import sys
import pathlib
import json

# Inject our helpers/ onto sys.path (same pattern as notify_owner.py)
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_scoopy_tasks import scoopy_get_tasks_for_today as _today_helper


def _render(result: dict) -> str:
    reply = result.get("reply", []) or []
    action_due = result.get("action_due", []) or []
    if not reply and not action_due:
        return (
            "No outstanding work for today. Nothing to draft, nothing waiting "
            "on a customer reply."
        )
    parts: list[str] = []
    parts.append(
        f"Daily worklist: {len(action_due)} ACTION due today, "
        f"{len(reply)} REPLY watching."
    )
    if action_due:
        parts.append("\n## ACTION (work today):")
        for t in action_due:
            line = f"- {t.get('title','(untitled)')}"
            if t.get("due_date"):
                line += f" — due {t['due_date']}"
            if t.get("contact_name"):
                line += f" [{t['contact_name']}]"
            if t.get("contact_id"):
                line += f" (contact {t['contact_id']})"
            parts.append(line)
            if t.get("body"):
                body = t["body"]
                if len(body) > 200:
                    body = body[:197] + "..."
                parts.append(f"  {body}")
    if reply:
        parts.append("\n## REPLY (watching only — no action needed unless reply arrives):")
        for t in reply:
            line = f"- {t.get('title','(untitled)')}"
            if t.get("contact_name"):
                line += f" [{t['contact_name']}]"
            if t.get("contact_id"):
                line += f" (contact {t['contact_id']})"
            parts.append(line)
    return "\n".join(parts)


class ScoopyGetTasksForToday(Tool):
    """Return Scoopy's daily worklist from the Firestore task cache."""

    async def execute(self, **kwargs) -> Response:
        try:
            result = _today_helper()
        except Exception as e:
            return Response(message=f"error: {e}", break_loop=False)
        rendered = _render(result)
        # Also append raw JSON so the agent can pluck specific fields if needed
        msg = (
            rendered
            + "\n\n```json\n"
            + json.dumps(result, indent=2, default=str)
            + "\n```"
        )
        return Response(message=msg, break_loop=False)
