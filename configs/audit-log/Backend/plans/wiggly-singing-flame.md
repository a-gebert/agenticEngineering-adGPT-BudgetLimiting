# Chat Session Audit Log — Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational skeleton for an immutable Chat Session Audit Log (Option B: Handler-driven Audit Context) that captures LLM call metadata at the `ChatStreamPersistingWrapper` injection point.

**Architecture:** A scoped `IChatAuditContext` is populated by `ChatStreamPersistingWrapper` (where Agent + ModelOptions are already loaded for the LLM call). A new `ChatSessionAuditInterceptor` reads this context during `SaveChangesAsync` and creates an immutable `ChatSessionAuditEntry` in the system "Audit" partition. Content storage is config-gated (AC-3, default off).

**Tech Stack:** .NET 8, EF Core, StronglyTypedIds, Cosmos DB / MongoDB / InMemory

---

## File Structure

### New Files

| File | Responsibility |
|---|---|
| `Shared/adessoGPT.Domain/PersistedEntities/System/Audit/ChatSessionAuditEntry.cs` | Immutable audit entry entity + StronglyTypedId |
| `Shared/adessoGPT.Core/Audit/IChatAuditContext.cs` | Scoped interface: handler populates, interceptor reads |
| `Shared/adessoGPT.Core/Audit/ChatAuditContext.cs` | Trivial scoped implementation |
| `Shared/adessoGPT.Core/Audit/ChatAuditData.cs` | Immutable data record passed via context |
| `Shared/adessoGPT.Core/Audit/ChatSessionAuditOptions.cs` | Config for content storage toggle (AC-3) |
| `Infrastructure/adessoGPT.Infrastructure.Persistence/Interceptors/ChatSessionAuditInterceptor.cs` | SaveChangesInterceptor that reads IChatAuditContext |
| `Infrastructure/.../Persistence.CosmosDb/Configurations/System/ChatSessionAuditEntryConfiguration.cs` | Cosmos DB entity config |
| `Infrastructure/.../Persistence.MongoDb/Configurations/System/ChatSessionAuditEntryConfiguration.cs` | MongoDB entity config |
| `Infrastructure/.../Persistence.InMemory/Configurations/System/ChatSessionAuditEntryConfiguration.cs` | InMemory entity config |

### Modified Files

| File | Change |
|---|---|
| `Shared/adessoGPT.Domain/ISystemDbContext.cs` | Add `DbSet<ChatSessionAuditEntry>` |
| `Infrastructure/.../Persistence/DependencyInjectionRegistrations.cs` | Register interceptor + scoped context |
| `Shared/adessoGPT.Core/CoreModule.cs` | Register `IChatAuditContext` as scoped |
| `Application/.../ChatStreamWrappers/ChatStreamPersistingWrapper.cs` | Inject `IChatAuditContext`, call `Capture()` after AssistantChatMessage construction (~line 160) |

---

## Task 1: Domain Entity — `ChatSessionAuditEntry`

**Files:**
- Create: `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/Audit/ChatSessionAuditEntry.cs`

- [ ] **Step 1: Create entity file**

Pattern: Follow `ConfigurationAuditEntry.cs` exactly. Inherit from `SystemAuditPartitionedEntity` (same "Audit" partition scope).

```csharp
namespace adessoGPT.Domain.PersistedEntities.System.Audit;

using System;
using System.Collections.Generic;
using adessoGPT.Domain.PersistedEntities.Base;
using adessoGPT.Domain.PersistedEntities.User.Conversation;
using adessoGPT.Domain.PersistedEntities.User.ChatMessage;
using StronglyTypedIds;

[StronglyTypedId(Template.Guid, "guid-efcore-openapi")]
public readonly partial struct ChatSessionAuditEntryId { }

public sealed record ChatSessionAuditEntry : SystemAuditPartitionedEntity
{
    public required ChatSessionAuditEntryId Id { get; init; }
    public required DateTimeOffset Timestamp { get; init; }
    public required UserId UserId { get; init; }
    public required string UserName { get; init; }

    // LLM call metadata (AC-1)
    public required string ModelId { get; init; }
    public required string ModelTitle { get; init; }
    public required ConversationId ConversationId { get; init; }
    public required ChatMessageId MessageId { get; init; }
    public string? TraceId { get; init; }

    // Model parameters snapshot (AC-1)
    public float? Temperature { get; init; }
    public int? MaxOutputTokens { get; init; }
    public float? TopP { get; init; }
    public float? FrequencyPenalty { get; init; }
    public float? PresencePenalty { get; init; }

    // Optional content (AC-3, config-gated, default OFF)
    public string? PromptContent { get; init; }
    public string? ResponseContent { get; init; }
}
```

- [ ] **Step 2: Verify build**

Run: `dotnet build`

- [ ] **Step 3: Commit**

```
feat(audit): add ChatSessionAuditEntry domain entity
```

---

## Task 2: Core — Audit Context Interface + Implementation

**Files:**
- Create: `Backend/Shared/adessoGPT.Core/Audit/IChatAuditContext.cs`
- Create: `Backend/Shared/adessoGPT.Core/Audit/ChatAuditContext.cs`
- Create: `Backend/Shared/adessoGPT.Core/Audit/ChatAuditData.cs`
- Create: `Backend/Shared/adessoGPT.Core/Audit/ChatSessionAuditOptions.cs`

- [ ] **Step 1: Create ChatAuditData record**

```csharp
namespace adessoGPT.Core.Audit;

public sealed record ChatAuditData
{
    // Model identification
    public required string ModelId { get; init; }
    public required string ModelTitle { get; init; }

    // Model parameters (snapshot at time of call)
    public float? Temperature { get; init; }
    public int? MaxOutputTokens { get; init; }
    public float? TopP { get; init; }
    public float? FrequencyPenalty { get; init; }
    public float? PresencePenalty { get; init; }

    // Content (populated only if config allows)
    public string? PromptContent { get; init; }
    public string? ResponseContent { get; init; }
}
```

- [ ] **Step 2: Create IChatAuditContext interface**

```csharp
namespace adessoGPT.Core.Audit;

public interface IChatAuditContext
{
    void Capture(ChatAuditData data);
    ChatAuditData? Current { get; }
    bool IsActive { get; }
}
```

- [ ] **Step 3: Create ChatAuditContext implementation**

```csharp
namespace adessoGPT.Core.Audit;

internal sealed class ChatAuditContext : IChatAuditContext
{
    public ChatAuditData? Current { get; private set; }
    public bool IsActive => Current is not null;

    public void Capture(ChatAuditData data)
    {
        Current = data;
    }
}
```

- [ ] **Step 4: Create ChatSessionAuditOptions**

```csharp
namespace adessoGPT.Core.Audit;

public sealed class ChatSessionAuditOptions
{
    public bool StorePromptContent { get; set; } = false;
    public bool StoreResponseContent { get; set; } = false;
}
```

- [ ] **Step 5: Verify build**

Run: `dotnet build`

- [ ] **Step 6: Commit**

```
feat(audit): add IChatAuditContext, ChatAuditData, and ChatSessionAuditOptions
```

---

## Task 3: DI Registration

**Files:**
- Modify: `Backend/Shared/adessoGPT.Core/CoreModule.cs`
- Modify: `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence/DependencyInjectionRegistrations.cs`
- Modify: `Backend/Shared/adessoGPT.Domain/ISystemDbContext.cs`

- [ ] **Step 1: Register IChatAuditContext as scoped in CoreModule.cs**

Add after `services.AddAuditServices(scanningAssemblies);`:

```csharp
services.AddScoped<IChatAuditContext, ChatAuditContext>();
```

- [ ] **Step 2: Add DbSet to ISystemDbContext.cs**

Add alongside `ConfigurationAuditEntries`:

```csharp
DbSet<ChatSessionAuditEntry> ChatSessionAuditEntries { get; }
```

- [ ] **Step 3: Add DbSet to AdessoGptDbContextBase**

Add the matching property in the DbContext base class.

- [ ] **Step 4: Verify build**

Run: `dotnet build`

- [ ] **Step 5: Commit**

```
feat(audit): register IChatAuditContext and add ChatSessionAuditEntry DbSet
```

---

## Task 4: Persistence Configurations (3 providers)

**Files:**
- Create: `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence.CosmosDb/Configurations/System/ChatSessionAuditEntryConfiguration.cs`
- Create: `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence.MongoDb/Configurations/System/ChatSessionAuditEntryConfiguration.cs`
- Create: `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence.InMemory/Configurations/System/ChatSessionAuditEntryConfiguration.cs`

- [ ] **Step 1: CosmosDb configuration**

Pattern: Follow `ConfigurationAuditEntryConfiguration` in same directory. Inherit `SystemContainerConfigurationBase<ChatSessionAuditEntry>`.

- [ ] **Step 2: MongoDB configuration**

Inherit `SystemCollectionConfigurationBase<ChatSessionAuditEntry>`. Collection name: `"chat_session_audit"`. Indexes on: `Timestamp`, `UserId`, `ConversationId`.

- [ ] **Step 3: InMemory configuration**

Inherit `SystemTableConfigurationBase<ChatSessionAuditEntry>`. Table name: `"ChatSessionAudit"`.

- [ ] **Step 4: Verify build**

Run: `dotnet build`

- [ ] **Step 5: Commit**

```
feat(audit): add ChatSessionAuditEntry persistence configurations for all 3 providers
```

---

## Task 5: ChatSessionAuditInterceptor

**Files:**
- Create: `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence/Interceptors/ChatSessionAuditInterceptor.cs`
- Modify: `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence/DependencyInjectionRegistrations.cs`

- [ ] **Step 1: Create interceptor**

Pattern: Mirror `ConfigurationAuditInterceptor` structure but read from `IChatAuditContext` instead of scanning ChangeTracker for `ISystemSetting`.

```csharp
internal class ChatSessionAuditInterceptor : SaveChangesInterceptor
{
    private readonly IChatAuditContext _chatAuditContext;
    private readonly IUserAccessor _userAccessor;
    private readonly TimeProvider _timeProvider;

    // Constructor with 3 dependencies

    public override ValueTask<InterceptionResult<int>> SavingChangesAsync(...)
    {
        ProcessChanges(eventData.Context);
        return base.SavingChangesAsync(...);
    }

    private void ProcessChanges(DbContext? context)
    {
        if (context is null || !_chatAuditContext.IsActive) return;

        // Find the AssistantChatMessage being Added in the ChangeTracker
        var assistantMessageEntry = context.ChangeTracker.Entries()
            .FirstOrDefault(e => e.Entity is AssistantChatMessage && e.State == EntityState.Added);

        if (assistantMessageEntry is null) return;

        var message = (AssistantChatMessage)assistantMessageEntry.Entity;
        var data = _chatAuditContext.Current!;
        var user = _userAccessor.User;

        var auditEntry = new ChatSessionAuditEntry
        {
            Id = ChatSessionAuditEntryId.New(),
            Timestamp = _timeProvider.GetUtcNow(),
            UserId = new UserId(user.Id.Value),
            UserName = user.Name,
            ModelId = data.ModelId,
            ModelTitle = data.ModelTitle,
            ConversationId = message.ConversationId,
            MessageId = message.Id,
            TraceId = Activity.Current?.TraceId.ToString(),
            Temperature = data.Temperature,
            MaxOutputTokens = data.MaxOutputTokens,
            TopP = data.TopP,
            FrequencyPenalty = data.FrequencyPenalty,
            PresencePenalty = data.PresencePenalty,
            PromptContent = data.PromptContent,
            ResponseContent = data.ResponseContent,
        };

        context.Set<ChatSessionAuditEntry>().Add(auditEntry);
    }
}
```

- [ ] **Step 2: Register interceptor in DependencyInjectionRegistrations.cs**

Add `services.AddScoped<ChatSessionAuditInterceptor>();` and chain `.AddInterceptors(serviceProvider.GetRequiredService<ChatSessionAuditInterceptor>())`.

- [ ] **Step 3: Verify build**

Run: `dotnet build`

- [ ] **Step 4: Commit**

```
feat(audit): add ChatSessionAuditInterceptor
```

---

## Task 6: Capture() Call in ChatStreamPersistingWrapper

**Files:**
- Modify: `Backend/Application/adessoGPT.Application/Business/Chat/ChatStreaming/CreateChatStream/ChatStreamWrappers/ChatStreamPersistingWrapper.cs` (~line 160)

- [ ] **Step 1: Inject IChatAuditContext + IOptions<ChatSessionAuditOptions>**

Add to constructor parameters and fields.

- [ ] **Step 2: Add Capture() call after AssistantChatMessage construction**

After `messageToPersist` is built (~line 160), before it's persisted (~line 163):

```csharp
var modelOptions = context.ModelExecutionSettings.ModelOptions;

_chatAuditContext.Capture(new ChatAuditData
{
    ModelId = modelOptions.ModelId.Value,
    ModelTitle = modelOptions.Title.Get(CultureInfo.InvariantCulture),
    Temperature = (modelOptions as ConversationalModelOptionsBase)?.Temperature,
    MaxOutputTokens = (modelOptions as ConversationalModelOptionsBase)?.MaxOutputTokens,
    TopP = (modelOptions as ChatModelOptionsBase)?.TopP,
    FrequencyPenalty = (modelOptions as ChatModelOptionsBase)?.FrequencyPenalty,
    PresencePenalty = (modelOptions as ChatModelOptionsBase)?.PresencePenalty,
    PromptContent = _auditOptions.Value.StorePromptContent ? context.CurrentMessage?.Content : null,
    ResponseContent = _auditOptions.Value.StoreResponseContent ? completeMessage.ToString() : null,
});
```

The `context` object (`ChatStreamContext`) already has `ModelExecutionSettings.ModelOptions` and `CurrentMessage` — no DB lookup needed.

- [ ] **Step 3: Verify build**

Run: `dotnet build`

- [ ] **Step 4: Commit**

```
feat(audit): capture chat audit data in ChatStreamPersistingWrapper
```

---

## Task 7: Verify End-to-End (Manual)

- [ ] **Step 1: Start backend with IntegrationTest profile**
- [ ] **Step 2: Send a chat message**
- [ ] **Step 3: Verify ChatSessionAuditEntry was created in the database**

---

## Open Points (for elaboration in follow-up tasks)

### Architecture

- [ ] **OP-1: Rename `IAuditService`** — Current name is misleading (it's a diff engine, not an audit service). Rename to `IEntityChangeDetectionService` or `IPropertyDiffService` to avoid confusion with the new chat audit.
- [ ] **OP-2: Generalize interceptor pattern** — Consider Strategy Pattern or Registry to avoid having N separate interceptors as audit types grow. Current plan adds a second interceptor alongside `ConfigurationAuditInterceptor`.
- [ ] **OP-3: System vs User partition decision** — Skeleton uses System partition (same as ConfigurationAuditEntry). Evaluate if user-partitioned storage is better for user-facing audit trail features.

### Compliance (AC-2: Immutability)

- [ ] **OP-4: Kryptografische Signatur** — Optional tamper-evidence via hash over entry fields. Define which fields are included, hash algorithm (SHA-256), and where the hash is stored (as a property on the entry).
- [ ] **OP-5: Append-only enforcement** — The skeleton has no update/delete handlers. Consider adding an EF Core interceptor or DB-level policy that rejects UPDATE/DELETE on audit entries.

### Compliance (AC-3: Content Storage)

- [ ] **OP-6: Admin configuration UI** — `ChatSessionAuditOptions` needs to be configurable via Control Center (FeatureFlags or SingleSettings). Define the admin workflow for enabling content storage.
- [ ] **OP-7: Content size limits** — Should prompt/response content be truncated to prevent oversized audit entries? Define max content length.

### Query & Endpoints

- [ ] **OP-8: Admin query endpoint** — `GET /api/control-center/chat-audit` with filters (UserId, ConversationId, ModelId, date range, pagination). Requires `ControlCenterAdmin` role.
- [ ] **OP-9: User-facing endpoint** — Should users see their own audit trail? `GET /api/user/audit` with user-scoped filtering.

### Testing

- [ ] **OP-10: Unit tests for ChatSessionAuditInterceptor** — Test that audit entry is created when context is active, skipped when inactive. Mock IUserAccessor, IChatAuditContext, TimeProvider.
- [ ] **OP-11: Unit tests for ChatAuditContext** — Test capture/read lifecycle, IsActive flag.
- [ ] **OP-12: Integration test** — End-to-end test that a chat message send produces an audit entry with correct model metadata.

### Data Model

- [ ] **OP-13: Agent metadata on entry** — Skeleton stores model info but not agent info (AgentId, AgentTitle). Add if agent tracking is required.
- [ ] **OP-14: Reasoning model parameters** — `ReasoningModelOptionsBase` has `ReasoningEffort` instead of Temperature. Capture this for reasoning models.
- [ ] **OP-15: Non-chat LLM calls** — The skeleton only captures chat stream calls. Internal LLM calls (title generation, topic analysis, data protection guard) are not audited. Define scope.
