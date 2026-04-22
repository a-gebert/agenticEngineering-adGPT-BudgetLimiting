# Chat Session Audit — Architecture Overview

## Context

The adessoGPT Audit system has two distinct audit types:

| Aspect | Configuration Audit | Chat Session Audit |
|--------|--------------------|--------------------|
| **Trigger** | Admin changes a system setting | User sends a chat message (LLM call) |
| **Volume** | Low (admin operations) | High (every LLM call) |
| **Pattern** | EF Core `SaveChangesInterceptor` | Explicit MediatR Command |
| **Container** | `"system"` (PK: `SystemScope = 'Audit'`) | `"system"` (PK: `SystemScope = 'UserChatAudit'`) |
| **Data** | Property-level diffs (old vs new) | LLM call snapshot (model, params, tokens) |

---

## System Overview

```mermaid
graph TB
    subgraph Frontend
        UI[AuditLogComponent<br/>+ SettingsComponent]
    end

    subgraph Presentation
        API[Chat Endpoint]
        CCAPI[ControlCenter ChatAudit Endpoints]
        SETAPI[ControlCenter Settings Endpoint]
    end

    subgraph Application
        CSW[ChatStreamPersistingWrapper]
        PAC[PersistChatSessionAuditEntryCommand]
        PAH[PersistChatSessionAuditEntryCommandHandler]
        EXP[StartChatAuditExportCommand]
        BG[ChatAuditExportBackgroundService]
        CLN[ChatSessionAuditCleanupHostedService]
        DEL[DeleteExpiredChatSessionAuditEntriesCommand]
    end

    subgraph Domain
        CSA[ChatSessionAuditEntry]
        SETS[ChatAuditLogSettings]
        ISC[ISystemDbContext]
    end

    subgraph Infrastructure
        CDB[(CosmosDB<br/>"system" container)]
        MDB[(MongoDB<br/>"system_chat_session_audit")]
        CACHE[(FusionCache<br/>export status)]
        STORE[(File Storage<br/>export blob)]
    end

    UI --> CCAPI
    UI --> SETAPI
    API --> CSW
    CSW --> PAC
    PAC --> PAH
    PAH -->|creates| CSA
    PAH --> ISC
    ISC --> CDB
    ISC --> MDB
    CCAPI --> EXP
    EXP --> BG
    BG --> CACHE
    BG --> STORE
    SETAPI --> SETS
    SETS --> ISC
    CLN --> DEL
    DEL --> ISC
```

---

## Data Flow: Write Path

```mermaid
sequenceDiagram
    participant User
    participant CSW as ChatStreamPersistingWrapper
    participant MediatR
    participant AMH as AppendMessageHandler
    participant UDB as User Container
    participant PAH as AuditHandler
    participant SDB as System Container

    User->>CSW: Chat message (streamed)
    Note over CSW: Collect streaming response<br/>Build AssistantChatMessage

    CSW->>MediatR: AppendMessageToConversationCommand
    MediatR->>AMH: Handle
    AMH->>UDB: SaveChanges (message + conversation)
    UDB-->>AMH: Success
    AMH-->>MediatR: Result.Success
    MediatR-->>CSW: persistResult

    Note over CSW: BuildAuditData() from context<br/>AgentId + Model params + token estimates

    CSW->>MediatR: PersistChatSessionAuditEntryCommand
    MediatR->>PAH: Handle
    Note over PAH: Enrich with:<br/>UserId (IUserAccessor)<br/>Timestamp (TimeProvider)<br/>TraceId (Activity.Current)<br/>ExpiresAt (RetentionDays setting)<br/>ContentHash (HMAC-SHA256)
    PAH->>SDB: SaveChanges (audit entry)
    SDB-->>PAH: Success
    PAH-->>MediatR: Result.Success
    MediatR-->>CSW: auditResult

    alt auditResult.IsFailure
        Note over CSW: Log warning, continue
    end

    CSW-->>User: ChatCompleteResponse
```

---

## Data Flow: Error Resilience

```mermaid
flowchart TD
    A[Message persist] -->|Success| B[Send audit command]
    A -->|Failure| X[Yield ChatErrorResponse<br/>Stop]

    B --> C{ErrorPipelineBehavior}
    C -->|Exception| D[Catches, returns Result.Failure]
    C -->|Success| E[Handler persists audit entry]

    D --> F{auditResult.IsFailure?}
    E --> G[Result.Success]
    G --> F

    F -->|Yes| H[Log warning]
    F -->|No| I[Continue]

    H --> J[Yield ChatCompleteResponse]
    I --> J

    style X fill:#f66,color:#fff
    style H fill:#fa0,color:#fff
    style J fill:#6c6,color:#fff
```

**Key principle:** A failed audit write never blocks the user's chat. The message is already persisted — the user gets their response regardless.

---

## Settings

### ChatAuditLogSettings

Stored as a `SingleSettings` document in the `"system"` container. Managed via the Control Center UI.

| Property | Type | Default | Description |
|---|---|---|---|
| `RetentionDays` | `int?` | `null` | Days after which entries expire. `null` = retain indefinitely. |

**Feature flag:** `"ChatAuditLog"` — gates all persistence and export operations. Implemented by `ChatAuditLogFeatureProvider`. Consumed via `IsChatAuditLogEnabledAsync()` extension method.

**Settings endpoint:** `GET/PUT /api/control-center/chat-audit-log-settings` (requires `ControlCenterAdmin`)

---

## API Endpoints

All endpoints under `/api/control-center/chat-audit` require `ControlCenterAdmin` role.

| Method | Route | Handler | Description |
|--------|-------|---------|-------------|
| `GET` | `/api/control-center/chat-audit` | `GetChatSessionAuditQueryHandler` | List audit entries (paginated, filtered) |
| `GET` | `/api/control-center/chat-audit/{id}` | `GetChatSessionAuditEntryByIdQueryHandler` | Get single entry by ID |
| `POST` | `/api/control-center/chat-audit/export` | `StartChatAuditExportCommandHandler` | Enqueue export job — returns `202 Accepted` + `exportId` |
| `GET` | `/api/control-center/chat-audit/export/{exportId}/status` | `GetChatAuditExportStatusQueryHandler` | Poll export job status |
| `GET` | `/api/control-center/chat-audit/export/{exportId}/download` | `DownloadChatAuditExportQueryHandler` | Download completed export file |
| `GET` | `/api/control-center/chat-audit-log-settings` | `GetControlCenterChatAuditLogSettingsQueryHandler` | Get settings |
| `PUT` | `/api/control-center/chat-audit-log-settings` | `UpsertControlCenterChatAuditLogSettingsCommandHandler` | Update settings |

**List query filters:** `UserId`, `ConversationId`, `ModelOptionsId`, `FromDate`, `ToDate`, `PageNumber`, `PageSize`

**Export filters:** `UserId`, `ModelOptionsId`, `FromDate`, `ToDate`, `Format` (currently `"json"` only)

---

## Export Pipeline

```mermaid
sequenceDiagram
    participant Handler as StartChatAuditExportCommandHandler
    participant BG as ChatAuditExportBackgroundService
    participant DB as System Container
    participant Fmt as JsonChatAuditExportFormatter
    participant Cache as FusionCache
    participant FS as File Storage

    Handler->>BG: Enqueue ChatAuditExportJob (exportId)
    Handler-->>API: 202 Accepted { exportId }

    Note over BG: Semaphore: max 2 concurrent jobs

    BG->>Cache: Set status = Processing
    BG->>DB: Query filtered ChatSessionAuditEntries
    DB-->>BG: Entries[]
    BG->>Fmt: FormatAsync(entries) → JSON bytes
    Fmt-->>BG: byte[]
    BG->>FS: Upload blob (1h expiration)
    FS-->>BG: blob key
    BG->>Cache: Set status = Completed + blob key (1h TTL)

    alt Error during processing
        BG->>Cache: Set status = Failed + errorMessage
    end
```

**Components:**

| Class | Responsibility |
|---|---|
| `StartChatAuditExportCommandHandler` | Validates filters, enqueues job, returns `exportId` |
| `ChatAuditExportBackgroundService` | `IHostedService`; channel-based queue; semaphore for concurrency |
| `ChatAuditExportJob` | Job payload: `ExportId`, `UserContext`, filter params |
| `ChatAuditExportEntry` | DTO for serialization (all IDs as strings) |
| `IChatAuditExportFormatter` / `JsonChatAuditExportFormatter` | Formats entries as indented camelCase JSON |
| `IChatAuditExportDownloadStrategy` / `StreamingChatAuditExportDownloadStrategy` | Streams file through backend (on-premise/MinIO) |
| `GetChatAuditExportStatusQueryHandler` | Reads status from FusionCache |
| `DownloadChatAuditExportQueryHandler` | Reads blob key from cache, delegates to download strategy |

---

## Frontend: Download Flow

```mermaid
sequenceDiagram
    participant User
    participant Comp as AuditLogComponent
    participant Store as AuditLogStore
    participant API as ControlCenter API

    User->>Comp: Fill filters + click "Export"
    Comp->>Store: startExport(filters)

    Store->>API: POST /api/control-center/chat-audit/export
    API-->>Store: 202 { exportId }
    Store->>Store: Set status = pending, start polling

    loop Poll every 2 seconds
        Store->>API: GET /api/control-center/chat-audit/export/{exportId}/status
        API-->>Store: { status: "processing" | "pending" | "completed" | "failed" }

        alt status = "completed"
            Store->>API: GET /api/control-center/chat-audit/export/{exportId}/download
            API-->>Store: application/json file stream
            Store->>Store: Create Blob URL
            Store->>Comp: Trigger <a href=blobUrl> click
            Comp->>User: Browser downloads audit-log.json
            Store->>Store: Revoke Blob URL
            Note over Store: Stop polling
        else status = "failed"
            Store->>Store: Set error state
            Comp->>User: Show error toast
            Note over Store: Stop polling
        end
    end
```

**State shape (NgRx Signals):**

| Signal | Type | Description |
|---|---|---|
| `exportStatus` | `'idle' \| 'pending' \| 'processing' \| 'completed' \| 'failed'` | Current export job state |
| `exportId` | `string \| null` | Active export job ID |
| `isExporting` | `boolean` (computed) | True while polling is active |
| `exportError` | `string \| null` | Error message if failed |

**Filter defaults:** `FromDate` = today minus 7 days, `ToDate` = today, `Format` = `"json"`

---

## Data Retention & Cleanup

```mermaid
flowchart LR
    A[PersistChatSessionAuditEntryCommandHandler] -->|RetentionDays set| B[ExpiresAt = now + RetentionDays]
    A -->|RetentionDays null| C[ExpiresAt = null<br/>retain indefinitely]

    D[ChatSessionAuditCleanupHostedService<br/>every 10 min] -->|feature flag enabled| E[DeleteExpiredChatSessionAuditEntriesCommand]
    E --> F[EF Core bulk delete<br/>WHERE ExpiresAt < UtcNow]
    F --> G[System Container]
```

- The `ExpiresAt` field is set at write time based on `ChatAuditLogSettings.RetentionDays`.
- `ChatSessionAuditCleanupHostedService` runs on a 10-minute interval and only executes if the feature flag is enabled.
- `DeleteExpiredChatSessionAuditEntriesCommandHandler` uses EF Core bulk delete for efficiency — no entity tracking.

---

## Container Architecture (CosmosDB)

```mermaid
graph LR
    subgraph CosmosDB Database
        subgraph "system" container
            direction TB
            S1[Settings<br/>PK: SystemScope = 'Settings']
            S2[ConfigurationAuditEntry<br/>PK: SystemScope = 'Audit']
            S3[Jobs<br/>PK: SystemScope = 'Jobs']
            S4[Stats<br/>PK: SystemScope = 'Stats']
            S5[ChatSessionAuditEntry<br/>PK: SystemScope = 'UserChatAudit']
        end

        subgraph "user" container
            direction TB
            U1[Conversations<br/>PK: UserId]
            U2[ChatMessages<br/>PK: UserId]
        end
    end

    style S2 fill:#69c,color:#fff
    style S5 fill:#4a9,color:#fff
```

### Partition Key Decision: `SystemScope = "UserChatAudit"`

| Query Pattern | Partition Behavior | Performance |
|--------------|-------------------|-------------|
| "All audit entries" (admin) | Single-partition | Fast |
| "Audit for user X" | Single-partition (filter by UserId) | Acceptable |
| "Audit for conversation Y" | Single-partition (filter by ConversationId) | Acceptable |

**Why a single shared partition?** All chat audit entries land in the `"UserChatAudit"` logical partition. This is acceptable for the expected volume — auditing LLM calls does not approach Cosmos DB hot-partition limits in practice. Sharing the `"system"` container avoids provisioning a dedicated container with its own minimum RU/s cost. The `SystemScope` value uniquely separates chat audit documents from all other system documents within the container.

---

## Entity Model

```mermaid
classDiagram
    class SystemPartitionedEntity {
        <<abstract record>>
        +SystemPartitionScope SystemScope
    }

    class ChatSessionAuditEntry {
        <<sealed record>>
        +ChatSessionAuditEntryId Id
        +UserId UserId
        +AgentId AgentId
        +ConversationId ConversationId
        +ChatMessageId MessageId
        +string ModelId
        +string ModelTitle
        +ModelOptionsId ModelOptionsId
        +string? TraceId
        +float? Temperature
        +int? MaxOutputTokens
        +float? TopP
        +float? FrequencyPenalty
        +float? PresencePenalty
        +ReasoningEffortLevel? ReasoningEffort
        +int? EstimatedPromptTokens
        +int? EstimatedResponseTokens
        +DateTimeOffset CreatedAt
        +DateTimeOffset? ExpiresAt
        +string? ContentHash
    }

    class ChatAuditData {
        <<sealed record>>
        +string AgentId
        +string ModelId
        +string ModelTitle
        +string ModelOptionsIdValue
        +float? Temperature
        +int? MaxOutputTokens
        +float? TopP
        +float? FrequencyPenalty
        +float? PresencePenalty
        +string? ReasoningEffort
        +int? EstimatedPromptTokens
        +int? EstimatedResponseTokens
        +DateTimeOffset CreatedAt
    }

    class ChatAuditLogSettings {
        <<SingleSettings record>>
        +int? RetentionDays
    }

    class PersistChatSessionAuditEntryCommand {
        <<ICommand>>
        +ChatAuditData AuditData
        +ConversationId ConversationId
        +ChatMessageId MessageId
    }

    SystemPartitionedEntity <|-- ChatSessionAuditEntry : inherits
    PersistChatSessionAuditEntryCommand --> ChatAuditData : carries
    PersistChatSessionAuditEntryCommand ..> ChatSessionAuditEntry : handler creates
    ChatAuditLogSettings ..> ChatSessionAuditEntry : gates ExpiresAt
```

### Content Hash

The `ContentHash` field is computed by `IContentIntegrityService` (HMAC-SHA256) over a JSON serialization of the entry's identifying fields: `UserId`, `AgentId`, `ModelId`, `ModelTitle`, `ModelOptionsId`, `ConversationId`, `MessageId`, `TraceId`, model parameters, token estimates, and `CreatedAt`. It enables post-hoc tamper detection.

---

## Comparison: Two Audit Patterns

```mermaid
flowchart LR
    subgraph "Configuration Audit (Interceptor)"
        CA1[Admin changes setting] --> CA2[SaveChanges triggered]
        CA2 --> CA3[ConfigurationAuditInterceptor<br/>fires in SaveChanges pipeline]
        CA3 --> CA4[Diff engine compares<br/>old vs new entity]
        CA4 --> CA5[ConfigurationAuditEntry<br/>added to same SaveChanges]
        CA5 --> CA6["system" container<br/>PK: SystemScope = 'Audit']
    end

    subgraph "Chat Session Audit (Command)"
        CS1[User sends chat] --> CS2[Message persisted<br/>to user container]
        CS2 --> CS3[Wrapper sends<br/>PersistChatSessionAuditEntryCommand]
        CS3 --> CS4[Handler builds<br/>ChatSessionAuditEntry]
        CS4 --> CS5[Separate SaveChanges<br/>to system container]
        CS5 --> CS6["system" container<br/>PK: SystemScope = 'UserChatAudit']
    end

    style CA3 fill:#69c,color:#fff
    style CS3 fill:#4a9,color:#fff
```

| Aspect | Configuration Audit | Chat Session Audit |
|--------|--------------------|--------------------|
| **Mechanism** | `SaveChangesInterceptor` | MediatR `ICommand` |
| **Trigger** | Automatic (any `ISystemSetting` change) | Explicit (after message persist) |
| **Transaction** | Same `SaveChanges` (intra-container) | Separate `SaveChanges` (same container, different partition) |
| **Error handling** | Fails with the setting change | Non-blocking (logged, never fails chat) |
| **Base class** | `SystemAuditPartitionedEntity` | `SystemPartitionedEntity` |
| **Container** | `"system"` | `"system"` |
| **Partition Key** | `SystemScope = 'Audit'` | `SystemScope = 'UserChatAudit'` |
| **Content** | Property diffs (old/new values) | LLM call snapshot |

---

## Layer Responsibilities

```mermaid
graph TD
    subgraph Domain Layer
        E[ChatSessionAuditEntry<br/>Sealed record]
        ID[ChatSessionAuditEntryId<br/>StronglyTypedId GUID]
        SETS_DOM[ChatAuditLogSettings<br/>SingleSettings record]
        ISC2[ISystemDbContext<br/>DbSet ChatSessionAuditEntries]
    end

    subgraph Core Layer
        CAD2[ChatAuditData<br/>DTO: AgentId + model params + token estimates]
        CIS[IContentIntegrityService<br/>HMAC-SHA256 hash]
    end

    subgraph Application Layer — Chat
        CMD[PersistChatSessionAuditEntryCommand]
        HDL[PersistChatSessionAuditEntryCommandHandler]
        WRP[ChatStreamPersistingWrapper<br/>Orchestrates persist + audit]
        CLN2[ChatSessionAuditCleanupHostedService<br/>10-min interval]
        DEL2[DeleteExpiredChatSessionAuditEntriesCommandHandler]
    end

    subgraph Application Layer — ControlCenter
        EXP2[StartChatAuditExportCommandHandler]
        BG2[ChatAuditExportBackgroundService]
        FMT[JsonChatAuditExportFormatter]
        DL[StreamingChatAuditExportDownloadStrategy]
        QRY[GetChatSessionAuditQueryHandler]
    end

    subgraph Infrastructure Layer
        COSMOS[CosmosDB Config<br/>ToContainer "system"<br/>HasPartitionKey SystemScope = 'UserChatAudit']
        MONGO[MongoDB Config<br/>ToCollection "system_chat_session_audit"]
        INMEM[InMemory Config<br/>ToTable "System_ChatSessionAudit"]
    end

    WRP --> CMD
    CMD --> HDL
    HDL --> ISC2
    HDL --> E
    HDL --> CIS
    WRP --> CAD2
    CLN2 --> DEL2
    DEL2 --> ISC2
    EXP2 --> BG2
    BG2 --> FMT
    BG2 --> DL
    QRY --> ISC2
    ISC2 --> COSMOS
    ISC2 --> MONGO
    ISC2 --> INMEM
```

---

## File Inventory

### Domain / Core

| Layer | File | Purpose |
|-------|------|---------|
| **Domain** | `Shared/.../Audit/ChatSessionAuditEntry.cs` | Entity (sealed record, `SystemPartitionedEntity`) |
| **Domain** | `Shared/.../SingleSettings/ChatAuditLogSettings.cs` | Retention settings stored in DB |
| **Core** | `Shared/.../Audit/ChatAuditData.cs` | DTO: AgentId + model params + token estimates |

### Application — Write Path

| Layer | File | Purpose |
|-------|------|---------|
| **Application** | `Application/.../ChatAudit/PersistChatSessionAuditEntryCommand.cs` | MediatR command |
| **Application** | `Application/.../ChatAudit/PersistChatSessionAuditEntryCommandHandler.cs` | Builds entity, computes hash, persists |
| **Application** | `Application/.../ChatStreamWrappers/ChatStreamPersistingWrapper.cs` | Orchestrates message + audit write |
| **Application** | `Application/.../ChatAudit/DeleteExpiredChatSessionAuditEntries/` | Bulk delete expired entries |
| **Application** | `Application/.../Jobs/ChatSessionAuditCleanupHostedService.cs` | 10-min cleanup loop |

### Application — ControlCenter

| Layer | File | Purpose |
|-------|------|---------|
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/ChatSessionAuditEndpoints.cs` | API routes |
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/GetChatSessionAudits/` | List query handler |
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/Export/ChatAuditExportBackgroundService.cs` | Async export worker |
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/Export/StartChatAuditExport/` | Enqueue export command |
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/Export/GetChatAuditExportStatus/` | Poll status query |
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/Export/DownloadChatAuditExport/` | Download query + strategy |
| **Application** | `Application.ControlCenter/.../ChatSessionAudit/Export/JsonChatAuditExportFormatter.cs` | JSON serialization |
| **Application** | `Application.ControlCenter/.../ChatAuditLogSettings/` | Settings CRUD handlers |

### Infrastructure

| Layer | File | Purpose |
|-------|------|---------|
| **Infrastructure** | `Infrastructure/.../CosmosDb/.../System/Audit/ChatSessionAuditEntryConfiguration.cs` | Container: `"system"`, PK: `SystemScope = 'UserChatAudit'` |
| **Infrastructure** | `Infrastructure/.../MongoDb/.../System/Audit/ChatSessionAuditEntryConfiguration.cs` | Collection: `"system_chat_session_audit"` |
| **Infrastructure** | `Infrastructure/.../InMemory/.../System/Audit/ChatSessionAuditEntryConfiguration.cs` | Table: `"System_ChatSessionAudit"` |

### Frontend

| Layer | File | Purpose |
|-------|------|---------|
| **Frontend** | `libs/control-center/.../audit-log/audit-log.component.ts` | Export UI (filters + trigger) |
| **Frontend** | `libs/control-center/.../audit-log/audit-log.store.ts` | NgRx Signals: export state + polling |
| **Frontend** | `libs/control-center/.../audit-log/chat-audit-log-settings/chat-audit-log-settings.component.ts` | Retention settings form |
| **Frontend** | `libs/control-center/.../audit-log/chat-audit-log-settings/chat-audit-log-settings.store.ts` | Settings load/save state |

### Tests

| Layer | File | Purpose |
|-------|------|---------|
| **Tests** | `Tests/.../Audit/PersistChatSessionAuditEntryCommandHandlerTests.cs` | Unit tests for handler |
| **Tests** | `Tests/.../Interceptors/AuditImmutabilityInterceptorTests.cs` | Immutability enforcement tests |
