"""Max mode: run one hard problem on the high end model, then go back.

Scoopy's everyday model is the cheap tier. Most of what he is asked is "what is
on today" or "look up this customer", and paying top rates for those is waste.
But some things are worth thinking hard about, and an approval that moves money
is the obvious one.

Agent Zero already had all the machinery: `allow_chat_override` is on, model
presets ship with the plugin (one of them is literally called "Max Power"), and
`chat_model_override` is scoped to a single conversation rather than globally.
This module is the small amount of policy on top.

The policy is the important part, because the failure mode here is money.

  Scoopy escalates himself   -> lasts ONE turn, then clears automatically
  a person turns it on       -> stays until they turn it off

That asymmetry is deliberate. Self-escalation with no confirmation is only safe
if it cannot persist: the danger is not one expensive answer, it is an agent
that quietly switches to the expensive model on a Tuesday and is still there on
Friday. A person flipping the switch knows they flipped it, so theirs sticks.

Clearing is done by the monologue_end extension, which runs when a turn
finishes, whether it finished well or badly.
"""
from __future__ import annotations
from typing import Any

from scoopy_logging import log

# Names from plugins/_model_config/default_presets.yaml. Resolved by name at
# call time rather than copied here: a preset edited in the UI must take effect
# without a code change, and a stale copy of a model id is how you end up
# quietly running last year's model.
MAX_PRESET = "Max Power"

# Where the scope lives on the conversation. Separate from Agent Zero's own
# `chat_model_override` so that clearing ours never disturbs an override a
# person set through /config for their own reasons.
_SCOPE_KEY = "scoopy_care_scope"
_OVERRIDE_KEY = "chat_model_override"


def current_mode(context: Any) -> str:
    """`max` or `everyday`, from whatever is actually in force."""
    override = context.get_data(_OVERRIDE_KEY) if context else None
    if isinstance(override, dict) and override.get("preset_name") == MAX_PRESET:
        return "max"
    return "everyday"


def engage(context: Any, *, scope: str, reason: str = "") -> bool:
    """Switch this conversation to the high end model.

    @param scope  `turn` for Scoopy's own call, cleared when the turn ends.
                  `thread` for a person's, which persists until turned off.
    @return       False if it was already on, so a caller can avoid announcing
                  a change that did not happen.
    """
    if scope not in ("turn", "thread"):
        raise ValueError(f"scope must be 'turn' or 'thread', got {scope!r}")

    already = current_mode(context) == "max"
    context.set_data(_OVERRIDE_KEY, {"preset_name": MAX_PRESET})

    # A person's choice outranks Scoopy's. If he escalates inside a thread
    # somebody has already pinned, the pin must survive the end of his turn,
    # so the wider scope wins rather than the most recent one.
    if context.get_data(_SCOPE_KEY) != "thread":
        context.set_data(_SCOPE_KEY, scope)

    log("care_mode_engaged", scope=scope, already_on=already, reason=reason[:200])
    return not already


def release(context: Any, *, only_if_turn_scoped: bool = False) -> bool:
    """Go back to the everyday model. Returns whether anything changed."""
    if current_mode(context) != "max":
        return False
    if only_if_turn_scoped and context.get_data(_SCOPE_KEY) != "turn":
        return False

    context.set_data(_OVERRIDE_KEY, None)
    context.set_data(_SCOPE_KEY, None)
    log("care_mode_released", only_if_turn_scoped=only_if_turn_scoped)
    return True
