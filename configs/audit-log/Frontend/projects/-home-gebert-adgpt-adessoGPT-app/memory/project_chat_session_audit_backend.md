---
name: Chat Session Audit — Backend Architecture
description: MediatR command-based audit for LLM chat calls — entity shape, container layout, error resilience, and current implementation status
type: project
---

**Pattern:** Explicit MediatR Command (`PersistChatSessionAuditEntryCommand`) — decoupled from the chat message persist. Audit failure never blocks the user.

**Why:** Chat is high-volume, async, and captures a snapshot (not a diff). Separate command allows fire-and-continue with proper error resilience.

**How to apply:** Frontend read API for Chat Session Audit does NOT yet exist. Backend write path is implemented. When a read endpoint is added, build a separate view from Configuration Audit (different data shape, different filters).

---

## Key Files (Backend)
- Entity: `Shared/adessoGPT.Domain/PersistedEntities/System/Audit/ChatSessionAuditEntry.cs`
- Command: `Application/adessoGPT.Application/Business/Chat/ChatAudit/PersistChatSessionAuditEntryCommand.cs`
- Handler: `Application/adessoGPT.Application/Business/Chat/ChatAudit/PersistChatSessionAuditEntryCommandHandler.cs`
- Options: `ChatSessionAuditOptions.cs` (`StorePromptContent`, `StoreResponseContent`)

---

## Container Layout (CosmosDB)
`system` container, `SystemScope = "UserChatAudit"` as partition key.

All three providers:
- CosmosDB: `system` container, PK `SystemScope = 'UserChatAudit'`
- MongoDB: collection `system_chat_session_audit`
- InMemory: table `System_ChatSessionAudit`

---

## ChatSessionAuditEntry Shape

```typescript
// When a read API is added, expect roughly this structure:
{
  id: string                   // ChatSessionAuditEntryId (GUID)
  timestamp: string            // ISO 8601 UTC
  userId: string
  userName: string
  modelId: string              // e.g. "gpt-4o"
  modelTitle: string           // e.g. "GPT-4o Standard"
  agentTitle: string           // e.g. "Research Agent"
  conversationId: string
  messageId: string
  traceId: string | null       // OpenTelemetry trace ID
  temperature: number | null
  maxOutputTokens: number | null
  topP: number | null
  frequencyPenalty: number | null
  presencePenalty: number | null
  promptContent: string | null   // only if StorePromptContent=true
  responseContent: string | null // only if StoreResponseContent=true
  integrityHash: string          // HMAC-SHA256 tamper evidence
}
```

---

## Error Resilience
- Chat message is persisted first (`AppendMessageToConversationCommand`)
- Audit command sent after successful message persist
- If audit fails: logged as warning, user still receives their chat response
- `ErrorPipelineBehavior` catches all exceptions and returns `Result.Failure`

---

## Current Status (2026-04-14)
- Write path: **fully implemented** (entity, command, handler, EF configs, tests)
- Read path (query API for frontend): **not yet implemented**
- Frontend UI: **not yet started**
