"""Render approval cards as HTMX-friendly HTML.

Pure module so it's unit-testable. The ApiHandler is a thin shell.
"""
from __future__ import annotations
from html import escape
from typing import Any


def render_card(token: str, card: dict[str, Any]) -> str:
    """Render a single pending approval card as HTML."""
    badge = escape(card.get("action_type", ""))
    contact = escape(card.get("contact_id", ""))
    reasoning = escape(card.get("reasoning", ""))
    draft = escape(card.get("draft", ""))
    pending = card.get("pending_actions", [])
    actions_html = ""
    if pending:
        actions_html = "<ul class='actions'>" + "".join(
            f"<li>{escape(a.get('skill','?'))}</li>" for a in pending
        ) + "</ul>"
    return (
        f'<div class="card" id="card-{escape(token)}">'
        f'<div class="badge badge-{badge}">{badge}</div>'
        f'<h3>{contact}</h3>'
        f'<p class="reasoning">{reasoning}</p>'
        f'<pre class="draft">{draft}</pre>'
        f'{actions_html}'
        f'<div class="buttons">'
        f'<button hx-post="/api/plugins/scoopy/scoopy_approve" hx-vals=\'{{"token":"{escape(token)}"}}\' hx-target="#card-{escape(token)}" hx-swap="outerHTML">Approve</button> '
        f'<button hx-post="/api/plugins/scoopy/scoopy_reject" hx-vals=\'{{"token":"{escape(token)}"}}\' hx-target="#card-{escape(token)}" hx-swap="outerHTML">Reject</button>'
        f'</div>'
        f'</div>'
    )


def render_inbox(pending: list[tuple[str, dict[str, Any]]]) -> str:
    """Render the full inbox page (or just the cards-content fragment)."""
    if not pending:
        return '<p class="empty">No pending cards.</p>'
    return "\n".join(render_card(t, c) for t, c in pending)
