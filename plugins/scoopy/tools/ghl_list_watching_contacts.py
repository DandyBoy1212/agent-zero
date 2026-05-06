"""ghl_list_watching_contacts Tool — bulk view of all contacts with the
`scoopy-watching` tag (i.e. everything Scoopy is mid-watching), optionally
with each contact's open `[REPLY]`/`[ACTION]` tasks merged in.

Read-only. break_loop=False so the agent keeps reasoning after the read.
"""
from __future__ import annotations
import sys
import pathlib

# Inject our helpers/ onto sys.path (same pattern as ghl_search_contact.py)
_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from skill_ghl_list_watching import ghl_list_watching_contacts as _list_helper
from ghl_client import GhlClient


def _coerce_bool(val, default: bool) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "y", "t")
    return bool(val)


def _render_markdown(contacts: list[dict]) -> str:
    if not contacts:
        return "No contacts currently tagged scoopy-watching. Nothing outstanding."
    lines: list[str] = [f"Found {len(contacts)} contact(s) tagged scoopy-watching:\n"]
    for c in contacts:
        header = f"- **{c.get('name') or '(unnamed)'}** (id `{c.get('id')}`)"
        bits = []
        if c.get("phone"):
            bits.append(c["phone"])
        if c.get("email"):
            bits.append(c["email"])
        if bits:
            header += " — " + " · ".join(bits)
        lines.append(header)
        tasks = c.get("tasks")
        if tasks is None:
            continue
        if not tasks:
            lines.append("    (no open Scoopy tasks)")
            continue
        for t in tasks:
            title = t.get("title", "(untitled)")
            due = t.get("dueDate", "")
            body = t.get("body", "")
            line = f"    - {title}"
            if due:
                line += f" — due {due}"
            if body:
                # Keep inline preview short
                preview = body if len(body) <= 120 else body[:117] + "..."
                line += f"\n      {preview}"
            lines.append(line)
        if c.get("tasks_error"):
            lines.append(f"    (tasks fetch error: {c['tasks_error']})")
    return "\n".join(lines)


class GhlListWatchingContacts(Tool):
    """List all contacts tagged scoopy-watching, optionally with their open tasks."""

    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        include_tasks = _coerce_bool(
            args.get("include_tasks", kwargs.get("include_tasks")), default=True
        )
        tag = args.get("tag") or kwargs.get("tag") or "scoopy-watching"

        try:
            client = GhlClient()
            contacts = _list_helper(
                client=client, include_tasks=include_tasks, tag=tag
            )
        except Exception as e:
            return Response(message=f"error: {e}", break_loop=False)

        return Response(message=_render_markdown(contacts), break_loop=False)
