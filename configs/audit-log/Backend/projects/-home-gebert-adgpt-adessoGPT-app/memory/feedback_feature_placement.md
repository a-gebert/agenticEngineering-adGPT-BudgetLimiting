---
name: Feature placement and architectural layer rules
description: Lessons learned from PR feedback on the Chat Session Audit export — where types, interfaces, and logic belong in the Clean Architecture layers
type: feedback
originSessionId: 4a9ba489-fd3d-4591-9ec9-bd468e3d6168
---
## What went wrong

Two architectural mistakes were caught in PR review on the Chat Session Audit feature:

### 1. Feature-specific types placed in the wrong layer (Core)

`ChatAuditOutcome`, `ChatAuditData`, `AuditIntegrityOptions`, and `IContentIntegrityService` were placed in `adessoGPT.Core/Audit/` alongside the *Configuration* Audit types (`IAuditEntityConfiguration`, `AuditService`, `CollectionDiffEngine`, etc.). Core is a shared foundation layer — it should only contain cross-cutting infrastructure, not feature-specific types.

**Correct placement:**

| Type | Layer | Reason |
|---|---|---|
| Enums/value types used by Domain entities | **Domain** | Entity depends on it, Domain has no upward references |
| DTOs, options classes, service interfaces consumed by Application handlers | **Application** | Business logic layer owns its contracts |
| Implementations of Application interfaces | **Infrastructure** | Dependency inversion — implements what Application defines |

Concrete example from this feature:
- `ChatAuditOutcome` (enum) → `Domain/PersistedEntities/System/Audit/` (used by `ChatSessionAuditEntry` entity)
- `ChatAuditData` (DTO) → `Application/Business/Chat/ChatAudit/` (used by command handlers)
- `AuditIntegrityOptions` (options) → `Application/Business/Chat/ChatAudit/` (registered in ApplicationModule)
- `IContentIntegrityService` (interface) → `Application/Business/Chat/ChatAudit/` (consumed by handler, implemented in Infrastructure)

### 2. Over-engineered export with unnecessary indirection

The export was implemented as a three-stage pipeline: POST to start a background job → poll status → download from Azure Blob Storage. This introduced `Channel<T>`, `BackgroundService`, `SemaphoreSlim`, `IFusionCache` for status tracking, `IChatAuditExportDownloadStrategy`, and blob storage upload — all for what should have been a single synchronous GET request that streams query results directly as a file response.

**Correct approach:** One GET endpoint → query DB → stream through formatter → return `TypedResults.Stream(...)`. No background processing, no blob storage, no status polling.

**Why:** The rule of thumb is: if the data source is a DB query with filters and the output is a formatted file, a direct streaming response is sufficient. Background processing is only warranted when the operation takes minutes (e.g., large batch jobs, external API aggregation) or when the result must be stored for later retrieval by a different client.

## How to apply

Before implementing a new feature, ask:

1. **Does the type describe a persisted entity or its direct dependencies (enums, value objects)?** → Domain
2. **Is it a DTO, options class, or interface consumed by command/query handlers?** → Application (in the feature's own folder, not in Core)
3. **Is it an implementation of an Application-defined interface?** → Infrastructure
4. **Is it truly cross-cutting and used by multiple unrelated features?** → Only then Core

For export/download features: start with the simplest approach (synchronous streaming) and only add complexity (background jobs, storage, polling) when there is a concrete performance or UX requirement.
