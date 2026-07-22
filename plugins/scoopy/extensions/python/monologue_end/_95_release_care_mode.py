"""Drop out of max mode when the turn Scoopy raised it for is over.

This is the thing that makes self-escalation safe to do without asking. Scoopy
can decide a problem is worth the expensive model and switch to it mid-answer,
with no card and no interruption, precisely because he cannot leave it on: this
runs when the turn ends and puts him back.

Only turn-scoped escalations are cleared. If a person pinned max mode for the
conversation, it stays pinned; releasing it here would silently undo a choice
they made deliberately and would look like the toggle was broken.

Numbered _95 so it runs after the standard monologue_end work.
"""
from __future__ import annotations
import pathlib
import sys

_HELPERS = pathlib.Path(__file__).resolve().parents[3] / "helpers"
if str(_HELPERS) not in sys.path:
    sys.path.insert(0, str(_HELPERS))

from helpers.extension import Extension
from agent import LoopData


class ReleaseCareMode(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Subordinate agents share the context but do not own the turn, so only
        # the top-level agent finishing means the turn is actually finished.
        if not self.agent or self.agent.number != 0:
            return
        try:
            from care_mode import release

            release(self.agent.context, only_if_turn_scoped=True)
        except Exception:
            # Never break the end of a turn over this. Worst case max mode
            # lingers for one more turn, which costs money but loses nothing,
            # whereas raising here would fail a reply that already succeeded.
            pass
