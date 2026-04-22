---
name: Language and clean code style
description: Respond in German, write all code/comments in English. Terse output, no trailing summaries.
type: feedback
---

User communicates in German — respond in German.
All code, comments, identifiers, and memory entries must be in English.

Only add comments for non-obvious design decisions. Never comment self-explanatory code.

Do not summarize what was just done at the end of a response — the user can read the diff.
Keep responses short and direct. Lead with the result, not the reasoning.

**Why:** Consistency across the codebase and team. Clean code should be readable without comments. User finds trailing summaries redundant.

**How to apply:** All new files use English. Responses in German. No trailing "Here is what I did" summaries.
