"""think_harder Tool — step up to the high end model for this problem.

Scoopy's everyday model is the cheap tier, which is right for "what is on
today" and wrong for anything where being wrong costs money. This is how he
says "this one is worth the good model" without stopping to ask.

He is allowed to do that without a card because it cannot persist: the
escalation is scoped to this turn and the monologue_end extension puts him back
afterwards. The risk of an agent quietly sitting on the expensive model for a
week is the reason for the scope, not a reason for a confirmation prompt.

It does not break the loop. Unlike notify_owner, which ends the turn because
the work is now waiting on a person, this changes how the rest of *this* turn is
answered, so the agent carries straight on with a better model under it.
"""
from __future__ import annotations
import pathlib
import sys

_HELPERS = pathlib.Path(__file__).resolve().parent.parent / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.tool import Tool, Response
from care_mode import current_mode, engage
from scoopy_logging import log


class ThinkHarder(Tool):
    async def execute(self, **kwargs) -> Response:
        args = getattr(self, "args", {}) or {}
        reason = str(args.get("reason") or kwargs.get("reason") or "").strip()
        log("tool_invoked", name="think_harder", has_reason=bool(reason))

        context = getattr(self.agent, "context", None)
        if context is None:
            return Response(message="error: no conversation to switch", break_loop=False)

        if current_mode(context) == "max":
            # Saying so plainly matters: without it he can call this repeatedly,
            # each time believing he has just improved his odds.
            return Response(
                message="Already on the high end model for this conversation. Carry on.",
                break_loop=False,
            )

        engage(context, scope="turn", reason=reason)
        log("tool_result", name="think_harder", outcome="engaged")
        return Response(
            message=(
                "Switched to the high end model for the rest of this turn. "
                "It goes back to the everyday model afterwards, so do the hard "
                "thinking now rather than assuming it will still be on later."
            ),
            break_loop=False,
        )
