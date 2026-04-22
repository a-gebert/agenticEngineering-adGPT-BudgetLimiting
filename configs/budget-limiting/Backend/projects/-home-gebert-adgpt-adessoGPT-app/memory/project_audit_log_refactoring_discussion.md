---
name: Audit Log Refactoring Discussion
description: Design discussion and agreed rough concept for extending the audit system — Option B (Handler-driven Audit Context) approved as approach for Chat Session Audit Log
type: project
originSessionId: 67b02ceb-c228-49ad-b75f-e8f2a2f46b55
---
# Audit Log Extension — Design Discussion (2026-04-13)

## Context

The existing Configuration Audit Log tracks property-level changes to ISystemSetting entities (admin settings). The goal is to extend audit support to **User Chat Session auditing** with specific compliance requirements (AC-1 through AC-3). During discussion, three architectural problems were identified and an approach was agreed upon.

## Agreed Approach: Option B — Handler-driven Audit Context

The handler already has all required data loaded (ModelOptions, Agent) for the LLM call. Instead of discarding it, the handler passes it to a scoped audit context. The interceptor reads the context at SaveChanges time and creates the audit entry — no additional DB lookups needed.

### Flow

```
Chat-Handler / PromptExecutor
  |
  +-- Loads ModelOptions (already needed for LLM call)
  +-- Loads Agent (already needed for SystemMessage)
  +-- _chatAuditContext.Capture(new ChatAuditData { ... })   // THE intervention point
  |
  +-- Executes LLM call
  +-- Saves AssistantChatMessage
  +-- SaveChangesAsync()
        |
        +-- Interceptor reads _chatAuditContext.Current
        +-- Creates ChatSessionAuditEntry (no DB lookup needed)
        +-- Appends to same transaction
```

### Key Interfaces

```csharp
public interface IChatAuditContext
{
    void Capture(ChatAuditData data);
    ChatAuditData? Current { get; }
}

public sealed record ChatAuditData
{
    public required string ModelId { get; init; }           // "gpt-4o"
    public required string ModelTitle { get; init; }        // "GPT-4o Standard"
    public required float? Temperature { get; init; }
    public required int? MaxOutputTokens { get; init; }
    public required string AgentTitle { get; init; }        // "Research Agent"
    // ... further parameters as needed
}
```

### What Gets Built (all additive, minimal change to existing code)

| Component | Location | Nature |
|---|---|---|
| `IChatAuditContext` + `ChatAuditData` | Core (new interface) | New |
| `ChatAuditContext` implementation | Core or Infrastructure | New, trivial |
| DI registration (Scoped) | `DependencyInjectionRegistrations` | 1 line |
| `Capture()` call | In handler/PromptExecutor where data is already loaded | **1 place — the only change to existing code** |
| `ChatSessionAuditInterceptor` | Infrastructure/Interceptors | New, ~80 lines |
| `ChatSessionAuditEntry` | Domain/Audit | New, sealed record |
| Persistence configs | 3x (Cosmos, Mongo, InMemory) | ~20 lines each |

### Open: Where exactly does the Capture() call sit?

Two candidates — needs investigation:
- **PromptExecutor** (infrastructure, catches ALL LLM calls) — broader, automatic
- **Concrete Chat-Command-Handler** (application, targeted) — more explicit, selective

## Compliance Requirements (PBI3270)

### AC-1: Required Fields per Audit Entry

| Field | Available? | Source at Interceptor Time |
|---|---|---|
| User-ID | Direct | `IUserAccessor.User.Id` |
| Timestamp (UTC, ISO 8601) | Direct | `TimeProvider.GetUtcNow()` |
| Used Model | Via ChatAuditData | `ChatAuditData.ModelId` (from ModelOptions, already loaded) |
| Model Parameters (Temperature, MaxTokens, etc.) | Via ChatAuditData | `ChatAuditData.Temperature`, `.MaxOutputTokens` etc. |
| Session/Request-ID | Partial | `ConversationId` as session + `Activity.Current?.TraceId` as request ID |

### AC-2: Immutability

- `sealed record` with `init`-only properties
- No update/delete handler or endpoint
- Append-only in Cosmos DB (natural mode)
- Optional: cryptographic signature (hash over entry, stored as property) — separate implementation step

### AC-3: Optional Content Storage

- `IOptions<ChatSessionAuditOptions>` with `bool StorePromptContent` and `bool StoreResponseContent`
- Default: `false` (content NOT stored)
- Admin activation via existing settings system (FeatureFlags or SingleSettings)
- Interceptor checks config before including content fields

## Conceptual Audit Entry Shape

```csharp
public sealed record ChatSessionAuditEntry : SystemAuditPartitionedEntity
{
    public required ChatSessionAuditEntryId Id { get; init; }
    public required DateTimeOffset Timestamp { get; init; }
    public required UserId UserId { get; init; }
    public required string UserName { get; init; }
    public required string ModelId { get; init; }             // "gpt-4o"
    public required string ModelTitle { get; init; }          // "GPT-4o Standard"
    public required string AgentTitle { get; init; }          // "Research Agent"
    public required ConversationId ConversationId { get; init; }
    public required ChatMessageId MessageId { get; init; }
    public string? TraceId { get; init; }                     // OpenTelemetry request trace
    // Model parameters (snapshot at time of call)
    public float? Temperature { get; init; }
    public int? MaxOutputTokens { get; init; }
    public float? TopP { get; init; }
    public float? FrequencyPenalty { get; init; }
    public float? PresencePenalty { get; init; }
    // Optional content (AC-3, config-gated)
    public string? PromptContent { get; init; }               // only if StorePromptContent=true
    public string? ResponseContent { get; init; }             // only if StoreResponseContent=true
}
```

## Reuse Analysis

### Reusable (Core Diff Engine)
- `IAuditService` / `AuditService` — pure object comparison, entity-agnostic (but needs rename, see below)
- `IAuditEntityConfiguration<T>` + fluent builder — works with any entity type
- `CollectionDiffEngine` — all 4 strategies
- `AuditPropertyChange` value object
- `AuditOperationType` enum
- `[AuditIgnore]`, `[SensitiveData]` attributes
- `IDisplayInfoService` + `[DisplayInfo]`

### NOT Reusable (Too Specialized)
- `ConfigurationAuditEntry` — bound to SystemAuditPartitionedEntity, no model/action fields
- `ConfigurationAuditInterceptor` — hard-filtered on ISystemSetting
- `ConfigurationAuditEndpoints` / query handlers — admin settings specific

## Three Architectural Problems Identified

### Problem 1: Naming — `IAuditService` is a Diff Engine

`IAuditService` does pure object comparison (GetAuditDifferences, MapToDisplayDifferences). It is a **Property Change Detection Service**, not an audit service. When we add a real chat audit, the naming collision will confuse.

**Why:** `AuditService` stores nothing, reads nothing from DB. It compares two objects and returns diffs.
**How to apply:** Rename to `IEntityChangeDetectionService` or `IPropertyDiffService` before or alongside the new work.

### Problem 2: Interceptor is Over-Specialized

`ConfigurationAuditInterceptor` is hard-wired to `ISystemSetting` + `ConfigurationAuditEntry`. Cannot be extended without if/else growth or duplication.

**Why:** The interceptor mixes decision logic (which entities?) with execution (diff + persist).
**How to apply:** For the chat audit, build a SEPARATE interceptor (`ChatSessionAuditInterceptor`) rather than trying to extend the existing one. Consider a Strategy Pattern later if more audit types emerge.

### Problem 3: Missing Abstraction Between Decision and Execution

The interceptor decides AND executes. These should be separated for extensibility.

**Why:** Each audit type (config vs chat session) has different decision criteria and different entry types.
**How to apply:** Option B's `IChatAuditContext` pattern naturally separates the decision (handler calls Capture) from execution (interceptor creates entry). This can be generalized later.

## Open Decisions (for later)

1. **Storage partition**: System-partition (admins query all users) vs User-partition (user sees own trail)?
2. **Capture() placement**: PromptExecutor (all LLM calls) vs specific command handler (selective)?
3. **Refactoring order**: Rename IAuditService + build chat audit in parallel? Or sequential?
4. **Cryptographic signature**: Scope and implementation for AC-2 tamper evidence?
