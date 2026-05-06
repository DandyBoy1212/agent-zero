"""scoopy_get_outstanding_tasks Tool — full open-task view.

Reads from the Firestore task cache (populated by the GHL task webhook).
Returns ALL open tasks assigned to Scoopy regardless of due date, split
by type: reply / action / other.

Read-only. break_loop=False.
"""
from __future__ import annotations
import sys
import pathlib
import json

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_scoopy_tasks import scoopy_get_outstanding_tasks as _outstanding_helper
from scoopy_logging import log, log_error


def _render(result: dict) -> str:
    reply = result.get("reply", []) or []
    action = result.get("action", []) or []
    other = result.get("other", []) or []
    total = len(reply) + len(action) + len(other)
    if total == 0:
        return "Nothing outstanding. Cache is empty for Scoopy."

    parts: list[str] = [
        f"Outstanding: {total} open task(s) — "
        f"{len(reply)} REPLY · {len(action)} ACTION · {len(other)} OTHER"
    ]
    for label, items in (("REPLY", reply), ("ACTION", action), ("OTHER", other)):
        if not items:
            continue
        parts.append(f"\n## {label}")
        for t in items:
            line = f"- {t.get('title','(untitled)')}"
            if t.get("due_date"):
                line += f" — due {t['due_date']}"
            if t.get("contact_name"):
                line += f" [{t['contact_name']}]"
            if t.get("contact_id"):
                line += f" (contact {t['contact_id']})"
            parts.append(line)
    return "\n".join(parts)


class ScoopyGetOutstandingTasks(Tool):
    """Return all outstanding Scoopy tasks (REPLY, ACTION, OTHER)."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        log("tool_invoked", name="scoopy_get_outstanding_tasks", args_keys=",".join(sorted(args.keys())))
        try:
            result = _outstanding_helper()
        except Exception as e:
            log_error("tool_result", e, name="scoopy_get_outstanding_tasks", outcome="error")
            return Response(message=f"error: {e}", break_loop=False)
        log("tool_result", name="scoopy_get_outstanding_tasks", outcome="success")
        rendered = _render(result)
        msg = (
            rendered
            + "\n\n```json\n"
            + json.dumps(result, indent=2, default=str)
            + "\n```"
        )
        return Response(message=msg, break_loop=False)
