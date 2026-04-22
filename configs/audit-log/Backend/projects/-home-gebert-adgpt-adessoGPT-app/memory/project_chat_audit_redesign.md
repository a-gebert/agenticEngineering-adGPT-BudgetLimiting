---
name: Chat Session Audit Redesign — Implemented
description: Redesigned ChatSessionAudit — eliminated Interceptor-Sideband pattern, moved to "system" Cosmos container with SystemScope = "UserChatAudit" partition, explicit MediatR command via ISystemDbContext
type: project
originSessionId: 2bade8f6-be80-4c82-8680-5df068eb575e
---
# Chat Session Audit Redesign (2026-04-14) — IMPLEMENTED

## What Changed

### Problem 1: Interceptor-Sideband -> Explicit MediatR Command
- **Removed:** `IChatAuditContext`, `ChatAuditContext`, `ChatSessionAuditInterceptor`
- **Added:** `PersistChatSessionAuditEntryCommand` + `PersistChatSessionAuditEntryCommandHandler`
- `ChatStreamPersistingWrapper` now sends the audit command after successful message persist
- Audit failures are logged but never block the chat (`ErrorPipelineBehavior` catches exceptions, wrapper checks `IsFailure`)

### Problem 2: Shared Container -> Dedicated Container -> Back to System Container
- **Original:** Audit data in shared `system` container (hot partition concern)
- **First redesign:** Dedicated `app-audit-logs` container with `AuditType` enum as partition key
- **Final (2026-04-14):** Moved back to `system` container to reduce database costs
  - `AuditType` enum deleted entirely
  - Entity inherits `SystemPartitionedEntity, ISystemPartitionedEntity` with `DefaultScope = new("UserChatAudit")`
  - Handler uses `ISystemDbContext` (not `IUserDbContext`)
  - EF configs use `SystemContainerConfigurationBase` / `SystemCollectionConfigurationBase` / `SystemTableConfigurationBase`

### Container Layout (Current)
- **CosmosDB:** `system` container, PK: `SystemScope = "UserChatAudit"`
- **MongoDB:** Collection `system_chat_session_audit`
- **InMemory:** Table `System_ChatSessionAudit`
- **Discriminator:** EF Core default (stores `"ChatSessionAuditEntry"` as discriminator value automatically)

### MediatR Wiring
- Handler in `adessoGPT.Application` is auto-discovered (assembly already scanned via `RegisterModule<ApplicationModule>()`)
- No new DI registrations — only removals of old interceptor/context registrations
- `ErrorPipelineBehavior` and `ValidationPipelineBehavior` apply automatically

## Key Files
- Entity: `Shared/adessoGPT.Domain/PersistedEntities/System/Audit/ChatSessionAuditEntry.cs`
- Command: `Application/adessoGPT.Application/Business/Chat/ChatAudit/PersistChatSessionAuditEntryCommand.cs`
- Handler: `Application/adessoGPT.Application/Business/Chat/ChatAudit/PersistChatSessionAuditEntryCommandHandler.cs`
- Tests: `Tests/Application/adessoGPT.Application.Tests/Audit/PersistChatSessionAuditEntryCommandHandlerTests.cs`
- Kept: `ChatAuditData.cs` (reused as DTO), `ChatSessionAuditOptions.cs` (still controls content storage)
- EF Configs: `Infrastructure/.../Configurations/System/ChatSessionAuditEntryConfiguration.cs` (3 providers)
