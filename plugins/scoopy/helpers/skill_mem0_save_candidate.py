"""mem0_save_candidate — queues a memory candidate for owner curation.

Does NOT save to Mem0 directly. Calls notify_owner with
action_type="memory_candidate" and a pending action of mem0_persist. Owner
approves in inbox -> dispatcher runs mem0_persist -> fact lands in Mem0
with provenance metadata.
"""
from __future__ import annotations
from typing import Any
from skill_notify_owner import notify_owner


def mem0_save_candidate(
    *,
    contact_id: str,  # routes the curation card to the right contact's inbox view
    namespace: str,
    fact: str,
    why_save: str,
) -> dict[str, Any]:
    return notify_owner(
        contact_id=contact_id,
        draft=fact,  # the candidate IS the "draft" in this card
        reasoning=why_save,
        action_type="memory_candidate",
        pending_actions=[
            {
                "skill": "mem0_persist",
                "args": {"namespace": namespace, "fact": fact},
            }
        ],
    )
