# Scoopy Plugin

Phase 2 supervised agent for Scoop Patrol. See the spec and plan in
`agentic-workflows-skill/.claude/worktrees/peaceful-elion-e1c35f/docs/superpowers/`.

## Layout

- `helpers/` — internal helpers (GHL HTTP client, auto-note formatter, approval store, etc.)
- `tools/` — agent-callable tools (notify_owner, mem0_search, etc.). Each subclasses `Tool` from `helpers/tool.py`.
- `api/` — webhook + inbox endpoints. Each subclasses `ApiHandler` from `helpers/api.py`.
- `prompts/` — prompt overrides for the Scoopy agent profile.
- `agents/scoopy/` — Scoopy agent profile.

## Approval mode

Every write goes through `notify_owner` → owner approves in inbox → `execute_with_approval` runs the underlying skill. Hardcoded — no bypass via prompt.
