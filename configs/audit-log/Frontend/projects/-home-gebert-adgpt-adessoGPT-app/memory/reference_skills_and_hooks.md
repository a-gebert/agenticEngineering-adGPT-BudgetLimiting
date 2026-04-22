---
name: Skills and Hooks — Frontend Config
description: Available skills and hooks configured for the Frontend Claude Code instance
type: reference
---

All configurations live in `/home/gebert/adgpt/agenticEngineering-adGPT-auditLog/configs/Frontend/`.

## Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `create-ui-component` | `/create-ui-component` | Step-by-step guide for creating Angular components: pre-flight, classification, component/store/route/i18n templates, kaseder checklist |
| `kaseder-review` | `/kaseder-review` | Reviews changed files against 10 kaseder convention categories; reports BLOCK/WARN/INFO findings |

## Hooks

| Hook | Trigger | File |
|------|---------|------|
| `architecture-check` | PostToolUse on Edit/Write/MultiEdit (`.component.ts`, `.store.ts`, `.component.html`, `.routes.ts`) | `hooks/architecture_check.py` |

The architecture-check hook emits a structured analysis prompt that Claude reads and acts on immediately for SEVERE findings (wrong inject placement, missing standalone/OnPush, ngClass, silent API failures, generic `:id` route params, etc.).

## Config Files
- `settings.json` — hooks registration + enabled plugins
- `skills/kaseder-review/SKILL.md` — kaseder skill definition
- `skills/create-ui-component/SKILL.md` — component creation skill definition
- `hooks/architecture_check.py` — architecture check hook script
