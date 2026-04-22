---
name: Claude config location
description: All Claude Code customizations (hooks, skills, settings) must be stored in the agenticEngineering repo, never in ~/.claude
type: feedback
originSessionId: c8a3fafe-09bc-40ba-86b5-9215169328fc
---
All Claude Code customizations — hooks, skills, settings.json, plugins config — must be stored in the project-specific agenticEngineering repo, not under `~/.claude`.

**Repo:** `/home/gebert/adgpt/agenticEngineering-adGPT-auditLog/configs/Backend/`

**Structure:**
- `settings.json` — Claude Code settings, hook registrations, plugin config
- `hooks/` — hook scripts (e.g. `worktree_guard.sh`)

**Why:** The agenticEngineering repo is version-controlled and project-specific. Storing config in `~/.claude` would make it global/machine-local and not shareable or auditable.

**How to apply:** When creating or modifying hooks, skills, or settings for this project, always target the agenticEngineering-adGPT-auditLog repo path. Never write to `~/.claude/settings.json` or `~/.claude/hooks/`.
