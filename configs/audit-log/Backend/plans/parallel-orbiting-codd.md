# Chat Session Audit Redesign

## Context

The current `ChatSessionAuditEntry` implementation has two architectural problems:

1. **Interceptor-Sideband pattern is over-engineered**: `ChatStreamPersistingWrapper` writes to `IChatAuditContext` (mutable scoped sideband), the `ChatSessionAuditInterceptor` reads it during `SaveChanges`. The Wrapper already has all the data — the indirection adds complexity without benefit.

2. **Wrong Cosmos container**: `ChatSessionAuditEntry` lands in the shared `"system"` container (PK = `SystemScope = "Audit"`) alongside low-volume admin settings. Chat audit is high-volume (one entry per LLM call) and needs independent RU/s, TTL, and indexing. Additionally, all audit entries share one logical partition ("Audit") → hot partition.

**Why the Interceptor's atomicity is illusory**: The message goes to the `"user"` container, the audit entry to `"system"`. CosmosDB doesn't support cross-container transactions — EF Core issues separate API calls. The Interceptor adds complexity without delivering its only benefit.

---

## Design Decisions

### Partition Key: `UserId`

The new `"audit"` container uses `UserId` as partition key.

**Why:**
- Even distribution across users (avoids single "Audit" hot partition)
- Aligns with primary query pattern: "show audit entries for user X" → single-partition query (fast)
- Admin "show all" queries become cross-partition → acceptable (rare, uses fan-out)
- Both `ConfigurationAuditEntry` and `ChatSessionAuditEntry` already have `UserId`

**How it gets set:** The wrapper passes `context.User.Id` into the command. The handler converts it to the domain `UserId` (implicit operator exists) and sets it on the entity. The CosmosDB configuration declares `builder.HasPartitionKey(e => e.UserId)`.

### Persist via MediatR Command (not Interceptor)

`ChatStreamPersistingWrapper` sends a `PersistChatSessionAuditEntryCommand` via MediatR after successful message persistence. The handler builds the entity and saves it to `ISystemDbContext`.

**Why:**
- Explicit, traceable data flow (no hidden sideband)
- `ErrorPipelineBehavior` catches exceptions → handler stays clean (no try-catch per project rules)
- Wrapper checks result: if failure → log warning, continue (audit never blocks chat)
- Only fires when message was actually persisted (cleaner than interceptor which fires during SaveChanges regardless of outcome)

**How it's wired (no extra registration needed):**
- `ChatStreamPersistingWrapper` already injects `IMediator` and uses it for `AppendMessageToConversationCommand` and `RenameConversationCommand`
- The new handler lives in `adessoGPT.Application` — this assembly is already scanned by MediatR via `RegisterModule<ApplicationModule>()` → `SetupCQRS(scanningAssemblies)` → `AddMediatR(cfg.RegisterServicesFromAssemblies(...))`
- Handler is auto-discovered, no manual DI registration
- `ErrorPipelineBehavior` and `ValidationPipelineBehavior` apply automatically (open generic behaviors)
- The only DI changes are **removals**: `IChatAuditContext` (CoreModule), `ChatSessionAuditInterceptor` + `.AddInterceptors()` (DependencyInjectionRegistrations)

### No new container base class (YAGNI)

Only `ChatSessionAuditEntry` goes to the `"audit"` container. One entity doesn't justify an `AuditContainerConfigurationBase`. The configuration uses `IEntityTypeConfiguration<T>` directly.

### ConfigurationAuditEntry stays in `"system"` container

Low-volume, working correctly, conceptually part of system settings management. No change.

---

## Implementation Steps

### Step 1: Modify entity — remove base class

**File:** `Shared/adessoGPT.Domain/PersistedEntities/System/Audit/ChatSessionAuditEntry.cs`

- Remove `: SystemAuditPartitionedEntity` inheritance
- The entity becomes a standalone `sealed record` with no base class
- All existing properties stay unchanged (entity already has `UserId`)
- The inherited `SystemScope` property disappears (no longer needed)

### Step 2: Create MediatR command + handler

**New:** `Application/adessoGPT.Application/Business/Chat/ChatAudit/PersistChatSessionAuditEntryCommand.cs`

```csharp
public record PersistChatSessionAuditEntryCommand : ICommand
{
    public required ChatAuditData AuditData { get; init; }
    public required ConversationId ConversationId { get; init; }
    public required ChatMessageId MessageId { get; init; }
}
```

Reuses existing `ChatAuditData` record for model fields. `UserId`, `UserName`, `Timestamp`, `TraceId` are resolved by the handler from its own dependencies (`IUserAccessor`, `TimeProvider`, `Activity.Current`).

**New:** `Application/adessoGPT.Application/Business/Chat/ChatAudit/PersistChatSessionAuditEntryCommandHandler.cs`

```csharp
internal class PersistChatSessionAuditEntryCommandHandler : ICommandHandler<PersistChatSessionAuditEntryCommand>
{
    private readonly ISystemDbContext _dbContext;
    private readonly IUserAccessor _userAccessor;
    private readonly TimeProvider _timeProvider;

    // Handler builds ChatSessionAuditEntry from command + infrastructure data
    // No try-catch — ErrorPipelineBehavior handles exceptions
}
```

### Step 3: Modify ChatStreamPersistingWrapper

**File:** `Application/adessoGPT.Application/Business/Chat/ChatStreaming/CreateChatStream/ChatStreamWrappers/ChatStreamPersistingWrapper.cs`

Changes:
- **Remove** `IChatAuditContext` dependency
- **Keep** `IOptions<ChatSessionAuditOptions>` (for `StorePromptContent` / `StoreResponseContent`)
- **Add** `ILogger<ChatStreamPersistingWrapper>` for logging audit failures
- **Remove** `CaptureChatAuditData()` method — replaced by inline `BuildAuditData()` that returns `ChatAuditData`
- **After successful message persist**, send command and handle failure gracefully:

```csharp
// After persistResult.IsSuccess, before yielding ChatCompleteResponse:
var auditResult = await _mediator.Send(
    new PersistChatSessionAuditEntryCommand
    {
        AuditData = BuildAuditData(context, completeMessage),
        ConversationId = context.ConversationId,
        MessageId = messageToPersist.Id,
    },
    cancellationToken
);

if (auditResult.IsFailure)
{
    _logger.LogWarning("Failed to persist chat session audit entry: {Error}", auditResult.Error);
}
```

### Step 4: Remove Interceptor + Sideband

**Delete:**
- `Infrastructure/adessoGPT.Infrastructure.Persistence/Interceptors/ChatSessionAuditInterceptor.cs`
- `Shared/adessoGPT.Core/Audit/IChatAuditContext.cs`
- `Shared/adessoGPT.Core/Audit/ChatAuditContext.cs`

**Modify:** `Infrastructure/adessoGPT.Infrastructure.Persistence/DependencyInjectionRegistrations.cs`
- Remove `services.AddScoped<ChatSessionAuditInterceptor>();` (line 22)
- Remove `.AddInterceptors(serviceProvider.GetRequiredService<ChatSessionAuditInterceptor>())` (line 32)

**Modify:** `Shared/adessoGPT.Core/CoreModule.cs`
- Remove `services.AddScoped<IChatAuditContext, ChatAuditContext>();` (line 29)

**Keep:**
- `ChatAuditData.cs` — reused as DTO in the command
- `ChatSessionAuditOptions.cs` — still used by wrapper

### Step 5: Update EF Core configurations

**CosmosDB:** `Infrastructure/adessoGPT.Infrastructure.Persistence.CosmosDb/Configurations/System/ChatSessionAuditEntryConfiguration.cs`

- Change from `SystemContainerConfigurationBase<ChatSessionAuditEntry>` to `IEntityTypeConfiguration<ChatSessionAuditEntry>`
- New container and partition key:

```csharp
public void Configure(EntityTypeBuilder<ChatSessionAuditEntry> builder)
{
    builder.ToContainer("audit");
    builder.HasPartitionKey(e => e.UserId);
    builder.HasNoDiscriminator();

    // ... existing property configurations unchanged ...
}
```

- No query filter needed (single entity type, admin queries see all entries)
- Consider moving file to `Configurations/Audit/` subfolder

**MongoDB:** `Infrastructure/adessoGPT.Infrastructure.Persistence.MongoDb/Configurations/System/ChatSessionAuditEntryConfiguration.cs`

- Change from `SystemCollectionConfigurationBase<ChatSessionAuditEntry>` to `IEntityTypeConfiguration<ChatSessionAuditEntry>`
- Collection name: `audit_chat_session` (new prefix aligned with container concept)
- Keep existing indexes (Timestamp, UserId, ConversationId)

**InMemory:** `Infrastructure/adessoGPT.Infrastructure.Persistence.InMemory/Configurations/System/ChatSessionAuditEntryConfiguration.cs`

- Change from `SystemTableConfigurationBase<ChatSessionAuditEntry>` to `IEntityTypeConfiguration<ChatSessionAuditEntry>`
- Table name: `Audit_ChatSession`

### Step 6: Update tests

**Delete:**
- `Tests/Application/adessoGPT.Application.Tests/Audit/ChatSessionAuditInterceptorTests.cs`
- `Tests/Application/adessoGPT.Application.Tests/Audit/ChatAuditContextTests.cs`

**New:** `Tests/Application/adessoGPT.Application.Tests/Audit/PersistChatSessionAuditEntryCommandHandlerTests.cs`

Test cases:
1. Happy path — all fields correctly mapped to entity
2. Timestamp comes from TimeProvider, not from command
3. TraceId captured from Activity.Current
4. Nullable model parameters mapped correctly
5. Optional content fields (PromptContent, ResponseContent) mapped through
6. Null content fields stored as null

### Step 7: Verify + build

- Search for all remaining references to deleted types (`IChatAuditContext`, `ChatAuditContext`, `ChatSessionAuditInterceptor`)
- Run `dotnet build` to verify compilation
- Run `dotnet csharpier format .` before committing

---

## File Summary

| Action | File |
|--------|------|
| **New** | `Application/.../Chat/ChatAudit/PersistChatSessionAuditEntryCommand.cs` |
| **New** | `Application/.../Chat/ChatAudit/PersistChatSessionAuditEntryCommandHandler.cs` |
| **New** | `Tests/.../Audit/PersistChatSessionAuditEntryCommandHandlerTests.cs` |
| **Delete** | `Infrastructure/.../Interceptors/ChatSessionAuditInterceptor.cs` |
| **Delete** | `Shared/adessoGPT.Core/Audit/IChatAuditContext.cs` |
| **Delete** | `Shared/adessoGPT.Core/Audit/ChatAuditContext.cs` |
| **Delete** | `Tests/.../Audit/ChatSessionAuditInterceptorTests.cs` |
| **Delete** | `Tests/.../Audit/ChatAuditContextTests.cs` |
| **Modify** | `Shared/.../Audit/ChatSessionAuditEntry.cs` — remove base class |
| **Modify** | `Application/.../ChatStreamPersistingWrapper.cs` — replace sideband with command |
| **Modify** | `Infrastructure/.../DependencyInjectionRegistrations.cs` — remove interceptor |
| **Modify** | `Shared/adessoGPT.Core/CoreModule.cs` — remove IChatAuditContext |
| **Modify** | `Infrastructure/.../CosmosDb/.../ChatSessionAuditEntryConfiguration.cs` — audit container |
| **Modify** | `Infrastructure/.../MongoDb/.../ChatSessionAuditEntryConfiguration.cs` — new base |
| **Modify** | `Infrastructure/.../InMemory/.../ChatSessionAuditEntryConfiguration.cs` — new base |
| **Keep** | `ChatAuditData.cs`, `ChatSessionAuditOptions.cs`, `SystemAuditPartitionedEntity.cs`, `ISystemDbContext.cs` |

---

## Verification

1. `dotnet build` — no compilation errors
2. `dotnet test --filter "FullyQualifiedName~PersistChatSessionAuditEntry"` — new handler tests pass
3. `dotnet test` — full test suite passes (no regressions)
4. Grep for deleted type names confirms no remaining references
5. `dotnet csharpier format .` — code formatted
