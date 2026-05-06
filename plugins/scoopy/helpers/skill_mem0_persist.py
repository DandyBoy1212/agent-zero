"""mem0_persist — actually writes to Mem0 with provenance.

Approval-gated: only invoked by execute_with_approval after the owner
approves a memory_candidate card. Adds a [Scoopy] auto-note to the contact
when the namespace is contact-scoped.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from mem0_client import Mem0Client
from auto_note import post_auto_note


def mem0_persist(
    *,
    namespace: str,
    fact: str,
    reasoning: str,
    approver: str,
    client,  # GhlClient passed by dispatcher (used for the auto-note)
    mem0_client: Mem0Client | None = None,
) -> dict[str, Any]:
    mc = mem0_client or Mem0Client()
    metadata = {
        "approved_by": approver,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "reason": reasoning,
    }
    try:
        res = mc.add(namespace=namespace, fact=fact, metadata=metadata)
    except Exception as e:
        # Auto-note the failure on the contact, if scoped to one
        if namespace.startswith("contact:"):
            cid = namespace.split(":", 1)[1]
            post_auto_note(
                client=client,
                contact_id=cid,
                action_name="mem0_persist",
                reason=reasoning,
                approver=approver,
                result=f"error: {type(e).__name__}: {e}",
            )
        return {"status": "error", "reason": f"{type(e).__name__}: {e}"}

    memory_id: Any = None
    if isinstance(res, dict):
        memory_id = res.get("id") or res.get("memory_id")
    elif isinstance(res, list) and res:
        first = res[0]
        if isinstance(first, dict):
            memory_id = first.get("id") or first.get("memory_id")

    if namespace.startswith("contact:"):
        cid = namespace.split(":", 1)[1]
        post_auto_note(
            client=client,
            contact_id=cid,
            action_name="mem0_persist",
            reason=reasoning,
            approver=approver,
            result=f"success: memory_id={memory_id}",
            payload_summary=f"Remembered: {fact[:300]}",
        )

    return {"status": "success", "memory_id": memory_id, "namespace": namespace}
