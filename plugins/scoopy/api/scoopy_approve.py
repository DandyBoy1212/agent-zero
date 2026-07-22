"""POST /api/plugins/scoopy/scoopy_approve

Consumes the approval token, runs queued skills via the dispatcher,
returns an HTML confirmation snippet (HTMX-friendly).

This endpoint deliberately does not require an API key (requires_api_key
is False below): it is reached by a human tapping an approval link in a
text message, and that phone never holds a relay key. The capability
token in the link is what authorizes the *action*.

`approver`, however, is a different kind of value: it is who gets written
into the audit trail as having approved. It arrives as a plain field in
the POST body/query string, which means it is entirely client-supplied
and nothing about the token proves who submitted it. Anyone holding a
valid approval token could set `approver` to a colleague's name and pin
their own action on that person -- a targeted misattribution, which is
worse than the old hardcoded "liam" (uniformly wrong, at least not
targeted).

So `approver` is trusted only when the request also carries a valid
X-API-KEY: that header is set exclusively by the command-centre relay,
which authenticates staff by their login before forwarding the request,
so a submitted `approver` behind a valid key is something the relay
actually vouches for. Any other caller -- including a phone tapping the
link directly, which is the expected common case -- gets "unknown"
recorded regardless of what it submitted. The key check never gates the
approval itself, only whose name is recorded; a missing/invalid key must
never turn into a 401 here. Do not "simplify" this by trusting the
submitted approver unconditionally -- that's the exact hole this closes.
"""
from __future__ import annotations
import json
import sys, pathlib
from html import escape
from typing import Any

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.api import ApiHandler, Response
from approval import ApprovalError
from dispatcher import execute_with_approval
from ghl_client import GhlClient
from relay_auth import RelayAuthError, check_relay_key
from scoopy_logging import log, log_error


class ScoopyApprove(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool: return False
    @classmethod
    def requires_api_key(cls) -> bool: return False
    @classmethod
    def requires_csrf(cls) -> bool: return False
    @classmethod
    def get_methods(cls) -> list[str]: return ["POST"]

    async def process(self, input: dict[str, Any], request) -> Response:
        token = (input or {}).get("token") or request.form.get("token") or request.args.get("token")
        if not token:
            log("approve_clicked", token_prefix=None)
            return Response('<div class="card error">missing token</div>', status=400, mimetype="text/html")
        log("approve_clicked", token_prefix=token[:6] if isinstance(token, str) else None)
        try:
            client = GhlClient()
            submitted_approver = (
                (input or {}).get("approver")
                or request.form.get("approver")
                or request.args.get("approver")
            )
            try:
                check_relay_key(request.headers.get("X-API-KEY"))
                # Caller proved it's the command-centre relay, which already
                # authenticated staff by login -- the submitted value is safe
                # to trust.
                approver = submitted_approver or "unknown"
            except RelayAuthError:
                # Caller is not the authenticated relay (the normal case: a
                # phone tapping the link). Never trust a client-supplied
                # name here -- record "unknown" and drop whatever was
                # submitted, regardless of what it says. The approval below
                # still proceeds; only attribution is affected.
                approver = "unknown"
            results = execute_with_approval(token=token, approver=approver, client=client)
        except ApprovalError as e:
            log("approval_rejected", token_prefix=token[:6], reason=str(e))
            return Response(f'<div class="card error">approval error: {escape(str(e))}</div>', status=400, mimetype="text/html")
        # What actually happened, as opposed to what was clicked.
        #
        # These are three different outcomes and they used to be one:
        #
        #   executed   at least one action ran and none failed
        #   partial    some ran, some failed
        #   nothing    the card carried no actions, or every action failed
        #
        # All three previously returned 200 with success styling, including the
        # empty case, whose entire summary was the string "no actions". The
        # command centre only checks res.ok, so a card that did nothing at all
        # rendered as a green "Approved by Liam Dand". That is exactly what
        # happened on 2026-07-22: a task-completion approval reported success
        # and the task stayed open, and Scoopy had to complete it directly
        # through the API afterwards.
        #
        # A tap is not a write. This endpoint now says which it was.
        ran = [r for r in results if (r.get("status") or "") not in ("error", "")]
        failed = [r for r in results if (r.get("status") or "") == "error"]
        if ran and not failed:
            outcome = "executed"
        elif ran and failed:
            outcome = "partial"
        else:
            outcome = "nothing"

        log(
            "approve_executed",
            token_prefix=token[:6],
            status=outcome,
            action_count=len(results),
            failed_count=len(failed),
            results_summary=",".join(str(r.get("status", "?")) for r in results) or "none",
        )

        # Content negotiation rather than a changed status code, deliberately.
        # The common caller is a phone tapping a link in a text message, and
        # that path renders this response as HTML via HTMX. Returning a 4xx or a
        # JSON body to it would turn a working confirmation into a broken one.
        # The relay asks for JSON explicitly and gets the detail it needs.
        wants_json = "application/json" in (request.headers.get("Accept") or "")
        if wants_json:
            return Response(
                json.dumps({
                    "outcome": outcome,
                    "ran": len(ran),
                    "failed": len(failed),
                    # Reasons, not payloads: enough to tell a person why nothing
                    # happened, without putting internals on a screen.
                    "reasons": [str(r.get("reason", "")) for r in failed if r.get("reason")],
                }),
                status=200,
                mimetype="application/json",
            )

        summary = " &middot; ".join(escape(str(r.get("status", "?"))) for r in results) or "no actions"
        css = "success" if outcome == "executed" else "error"
        headline = {
            "executed": "Approved &rarr;",
            "partial": "Approved, but some of it failed &rarr;",
            "nothing": "Approved, but nothing ran &rarr;",
        }[outcome]
        return Response(
            f'<div class="card {css}">{headline} {summary}</div>',
            status=200,
            mimetype="text/html",
        )
