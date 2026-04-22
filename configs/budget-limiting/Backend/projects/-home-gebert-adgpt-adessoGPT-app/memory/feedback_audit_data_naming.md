---
name: ChatAuditData string field naming
description: In ChatAuditData, string fields that transport ID values use the domain name without a 'Value' suffix
type: feedback
originSessionId: 91ae598b-2d27-41b4-ab92-e817e1b07dbf
---
In `ChatAuditData`, string fields that carry the underlying value of a strongly-typed ID are named after the concept only — no `Value` suffix.

**Why:** `ModelId` is a plain `string` in `ChatAuditData` (not `ModelIdValue`). The suffix would be inconsistent and was flagged as wrong when `AgentIdValue` was proposed — it should be `AgentId`.

**How to apply:** When adding a string field to `ChatAuditData` that holds a strongly-typed ID's value, name it `AgentId`, `ModelId`, etc. — not `AgentIdValue` or `ModelIdValue`. The `Value` suffix is only acceptable on the single existing `ModelOptionsIdValue` field (already there as legacy).
