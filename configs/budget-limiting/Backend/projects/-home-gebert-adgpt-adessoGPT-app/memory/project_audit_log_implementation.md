---
name: Audit Log Implementation
description: Complete documentation of the Configuration Audit Log system — architecture, data flow, abstraction layers, immutability analysis, and file inventory
type: project
originSessionId: 67b02ceb-c228-49ad-b75f-e8f2a2f46b55
---
# Configuration Audit Log — Implementation Documentation

**Last updated:** 2026-04-13
**Branch:** feature/PBI3270_Audit_Log
**Scope:** Configuration changes only (system settings modified by administrators)

---

## 1. Architecture Overview

```
+-----------------------------------------------------------------------+
|                        PRESENTATION LAYER                              |
|  ConfigurationAuditEndpoints                                           |
|  GET /api/control-center/audit          (paginated, filtered query)    |
|  GET /api/control-center/audit/entity-types  (auditable type catalog)  |
|  RequireRole: ControlCenterAdmin                                       |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
|                        APPLICATION LAYER                               |
|  GetConfigurationAuditQueryHandler      (reads + maps to display DTOs) |
|  GetConfigurationAuditQueryValidator    (pagination + date range)      |
|  GetAuditEntityTypesQueryHandler        (returns type catalog)         |
+-----------------------------------+-----------------------------------+
                                    |
                        +-----------+-----------+
                        |                       |
                        v                       v
+-------------------------------+  +-----------------------------+
|       CORE / SHARED           |  |    DOMAIN                   |
|  IAuditService (singleton)    |  |  ConfigurationAuditEntry    |
|  AuditService                 |  |  AuditPropertyChange        |
|  IAuditEntityConfiguration<T> |  |  AuditOperationType (enum)  |
|  AuditEntityConfigurationBuilder  |  IAuditableEntity          |
|  CollectionDiffEngine         |  |  SystemAuditPartitionedEntity|
|  AuditPropertyMetadata        |  |  ConfigurationAuditEntryId  |
|  AuditEntityMetadata          |  +-----------------------------+
|  AuditCollectionMetadata      |
|  AuditDifference              |
|  AuditDifferencesResult       |
|  AuditDifferenceDisplay       |
|  AuditedEntityTypeInfo        |
|  AuditedEntityTypeCategory    |
|  [AuditIgnore] attribute      |
+-------------------------------+
                        |
                        v
+-----------------------------------------------------------------------+
|                     INFRASTRUCTURE LAYER                               |
|  ConfigurationAuditInterceptor (SaveChangesInterceptor, scoped)       |
|  +-- Updates IAuditableEntity timestamps (CreatedAt/By, ModifiedAt/By)|
|  +-- Generates ConfigurationAuditEntry for ISystemSetting changes     |
|                                                                        |
|  EF Core Entity Configurations:                                        |
|  +-- InMemory:  ConfigurationAuditEntryConfiguration (table)          |
|  +-- CosmosDb:  ConfigurationAuditEntryConfiguration (container)      |
|  +-- MongoDb:   ConfigurationAuditEntryConfiguration (collection)     |
+-----------------------------------------------------------------------+
```

---

## 2. Data Flow: Write Path (Audit Entry Creation)

```
Admin changes a system setting (Agent, Theme, ModelOptions, etc.)
         |
         v
EF Core SaveChanges / SaveChangesAsync triggered
         |
         v
ConfigurationAuditInterceptor.ProcessChanges()
         |
         +---> 1. UpdateAuditableEntityTimestamps()
         |         Sets CreatedBy/CreatedAt (Added) or ModifiedBy/ModifiedAt (Modified)
         |         via IUserAccessor + TimeProvider
         |
         +---> 2. GenerateAuditEntries()
                   |
                   +---> Filters ChangeTracker entries:
                   |     - Must be ISystemSetting
                   |     - Must be IsAudited(entityType) = true
                   |     - Must be Added | Modified | Deleted
                   |
                   +---> For each qualifying entry:
                   |     |
                   |     +---> Reconstruct old entity:
                   |     |     Added   -> oldEntity = null, newEntity = currentEntity
                   |     |     Modified -> oldEntity = OriginalValues.ToObject(), newEntity = currentEntity
                   |     |     Deleted  -> oldEntity = OriginalValues.ToObject(), newEntity = null
                   |     |
                   |     +---> IAuditService.GetAuditDifferences(oldEntity, newEntity)
                   |     |     Pure object comparison (EF Core independent)
                   |     |     Returns AuditDifferencesResult
                   |     |
                   |     +---> Skip if !HasDifferences
                   |     |
                   |     +---> Create ConfigurationAuditEntry record
                   |     |     - Id = ConfigurationAuditEntryId.New() (GUID)
                   |     |     - Timestamp from TimeProvider
                   |     |     - UserId + UserName from IUserAccessor
                   |     |     - EntityType = type.Name (string)
                   |     |     - EntityId = primary key.ToString()
                   |     |     - OperationType = Create | Update | Delete
                   |     |     - Changes = List<AuditPropertyChange>
                   |     |
                   |     +---> context.Set<ConfigurationAuditEntry>().Add(auditEntry)
                   |
                   +---> Audit entry is saved in the SAME transaction as the entity change
```

---

## 3. Data Flow: Read Path (Audit Query)

```
GET /api/control-center/audit?entityType=Agent&pageNumber=1&pageSize=25
         |
         v
GetConfigurationAuditQueryValidator
         |  - PageNumber >= 1, PageSize 1..100
         |  - FromDate <= ToDate
         v
GetConfigurationAuditQueryHandler.Handle()
         |
         +---> Build IQueryable from ISystemDbContext.ConfigurationAuditEntries
         |     Apply optional filters: EntityId, EntityType, UserName, FromDate, ToDate
         |
         +---> Count total + paginate (OrderByDescending Timestamp)
         |
         +---> For each entry:
         |     |
         |     +---> Reconstruct AuditDifferencesResult from stored Changes
         |     |     (resolve EntityType string -> Type via domain assembly reflection)
         |     |
         |     +---> IAuditService.MapToDisplayDifferences(differencesResult)
         |     |     - Looks up DisplayInfoAttribute for localized property titles
         |     |     - Falls back to KnownPropertyNames for renamed properties
         |     |     - Falls back to PropertyPath as display title
         |     |
         |     +---> Map to ConfigurationAuditEntryDto with AuditPropertyChangeDto[]
         |
         +---> Return GetConfigurationAuditResponse with pagination metadata
```

---

## 4. Difference Detection Engine

```
IAuditService.GetAuditDifferences(old, new)
         |
         v
AuditService.GetAuditDifferencesInternal()
         |
         +---> ResolveMetadata(entityType)
         |     - FrozenDictionary lookup (startup-built)
         |     - ConcurrentDictionary cache for derived types
         |     - Walks type hierarchy for polymorphic support
         |
         +---> For each AuditPropertyMetadata:
               |
               +---> [Collection property] -> CollectionDiffEngine.DiffCollection()
               |     |
               |     +---> KeyBased:           Match by Id, diff properties
               |     +---> SetBased:           JSON value equality, report added/removed
               |     +---> ScalarSet:          Value equality for primitives/IDs/enums
               |     +---> DictionaryKeyBased: Match by dict key, diff values
               |
               +---> [Scalar/Complex property]
                     |
                     +---> Create: all new values reported (old = null)
                     +---> Delete: all old values reported (new = null)
                     +---> Update: compare via Object.Equals, report if different
                     +---> Sensitive: values replaced with "***REDACTED***"
                     +---> Serialization: System.Text.Json, WriteIndented=false
```

---

## 5. Configuration System (Fluent Builder)

```
Entity defines inner class implementing IAuditEntityConfiguration<TEntity>
         |
         v
Discovered at startup via assembly scanning (AuditServiceRegistrationExtensions)
         |
         v
AuditEntityConfigurationBuilder<TEntity>
  |
  +---> AuditAllProperties()         -- auto-discovers all public properties recursively
  |     (excludes IAuditableEntity props via [AuditIgnore])
  |     (auto-detects [SensitiveData] attribute)
  |     (auto-detects collections + diff strategies)
  |
  +---> Property<T>(expr)            -- audit specific scalar property
  |     +---> .WithKnownPropertyNames()  -- backward compat for renames
  |     +---> .AsSensitive()             -- redact values
  |
  +---> ComplexProperty<T>(expr)     -- audit nested complex type
  |     +---> .AuditAllProperties()
  |     +---> .Property<T>(expr)
  |     +---> .Ignore<T>(expr)
  |
  +---> Collection<T>(expr)          -- audit collection with element diffing
  |     +---> .WithKey<K>(expr)          -- override key detection
  |     +---> .IgnoreElementProperty()   -- exclude element props
  |     +---> .WithKnownPropertyNames()
  |     +---> .AsSensitive()
  |
  +---> Ignore<T>(expr)              -- exclude property (and nested children)
         |
         v
Build() -> IReadOnlyList<AuditPropertyMetadata>
         |
         v
Stored in FrozenDictionary<Type, AuditEntityMetadata> (startup, immutable)
```

**Collection diff strategy auto-detection:**
- Dictionary types -> `DictionaryKeyBased`
- Scalar elements (primitives, enums, strongly-typed IDs, LocalizationStrings) -> `ScalarSet`
- Complex elements with `Id` property -> `KeyBased`
- Complex elements without `Id` -> `SetBased`

**27 entity types currently have audit configurations** (see grep results for `IAuditEntityConfiguration` in Domain).

---

## 6. Abstraction Layer Analysis

### Layer Boundaries

| Layer | Responsibility | Key Abstractions |
|-------|---------------|-----------------|
| **Domain** | Entity definitions, value objects, enums | `ConfigurationAuditEntry`, `AuditPropertyChange`, `AuditOperationType`, `IAuditableEntity`, `ISystemSetting` (marker) |
| **Core** | Business logic, difference detection, configuration API | `IAuditService`, `IAuditEntityConfiguration<T>`, builders, metadata records, `CollectionDiffEngine`, `[AuditIgnore]` |
| **Application** | CQRS handlers, DTOs, endpoints, validation | `GetConfigurationAuditQuery/Handler/Response`, `GetAuditEntityTypesQuery/Handler/Response`, `ConfigurationAuditEndpoints` |
| **Infrastructure** | EF Core interception, DB configurations | `ConfigurationAuditInterceptor`, `ConfigurationAuditEntryConfiguration` (x3 providers) |

### Key Abstraction Decisions

1. **EF Core independent comparison**: `AuditService` does pure object comparison via reflection — no dependency on EF Core change tracker for the diff logic itself. The interceptor bridges EF Core events to the audit service.

2. **Provider-agnostic persistence**: The same `ConfigurationAuditEntry` entity is configured for InMemory, CosmosDb, and MongoDb via separate `ConfigurationAuditEntryConfiguration` classes following the existing pattern.

3. **Display info decoupled from diff engine**: `MapToDisplayDifferences()` is a separate step from `GetAuditDifferences()`. The diff engine produces raw `AuditDifference` with JSON-serialized values; the display mapper adds localized titles via `IDisplayInfoService`.

4. **Configuration as code**: Audit configurations are co-located with domain entities as inner classes implementing `IAuditEntityConfiguration<T>`. This follows the EF Core `IEntityTypeConfiguration<T>` pattern.

5. **Polymorphic hierarchy support**: Abstract base types can define audit configs. Concrete types MUST also define their own config (validated at startup). Metadata is merged via type hierarchy traversal.

---

## 7. Immutability Analysis

### Fully Immutable (sealed record + init-only)

| Type | Location | Assessment |
|------|----------|------------|
| `ConfigurationAuditEntry` | Domain | `sealed record`, all `init` props |
| `AuditPropertyChange` | Domain | `sealed record`, all `init` props |
| `SystemAuditPartitionedEntity` | Domain | `abstract record` |
| `AuditDifference` | Core | `sealed record`, all `init` props |
| `AuditDifferencesResult` | Core | `sealed record`, `IReadOnlyList<>` |
| `AuditDifferenceDisplay` | Core | `sealed record`, all `init` props |
| `AuditPropertyMetadata` | Core | `sealed record`, `IReadOnlyList<>` |
| `AuditEntityMetadata` | Core | `sealed record`, `IReadOnlyList<>` |
| `AuditCollectionMetadata` | Core | `sealed record`, `IReadOnlyList<>` |
| `AuditedEntityTypeInfo` | Core | `sealed record`, all `init` props |
| `AuditedEntityTypeCategory` | Core | `sealed record`, `IReadOnlyList<>` |
| All Application DTOs | Application | `record`, all `init` props |

### Immutability Gaps

| Type/Property | Issue | Risk | Recommended Fix |
|---------------|-------|------|-----------------|
| `ConfigurationAuditEntry.Changes` | **`List<AuditPropertyChange>`** (mutable collection) | Low — entity is created once in interceptor, then persisted. But technically mutatable after construction. | Change to `IReadOnlyList<AuditPropertyChange>` |
| `ConfigurationAuditEntryDto.Changes` | **`List<AuditPropertyChangeDto>`** (mutable collection) | Low — DTO created in handler, serialized to HTTP response. | Change to `IReadOnlyList<AuditPropertyChangeDto>` |
| `AuditPropertyBuilderEntry` | **Mutable class** with settable properties | None — internal to builder, used only during startup configuration building. Correct design for builder pattern. | No change needed |
| `AuditEntityConfigurationBuilder<T>` | Mutable internal dictionaries | None — mutable during `Configure()` call, then `Build()` produces immutable output. Correct builder pattern. | No change needed |

### Runtime Immutability of AuditService State

| State | Type | Mutability |
|-------|------|-----------|
| `_baseConfigurations` | `FrozenDictionary<Type, AuditEntityMetadata>` | **Immutable** (frozen at startup) |
| `_resolvedCache` | `ConcurrentDictionary<Type, AuditEntityMetadata?>` | **Append-only** (thread-safe cache, never removes entries) |
| `_auditedEntityTypeCategories` | `IReadOnlyList<AuditedEntityTypeCategory>` | **Immutable** (built at startup) |
| `SerializerOptions` | `static readonly JsonSerializerOptions` | **Immutable** |

**Assessment: The AuditService is effectively immutable after startup.** The `ConcurrentDictionary` is append-only (caching derived type metadata on first access). All other state is frozen/readonly.

---

## 8. File Inventory

### Domain Layer (4 files)
- `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/Audit/ConfigurationAuditEntry.cs`
- `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/Audit/AuditPropertyChange.cs`
- `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/Audit/SystemAuditPartitionedEntity.cs`
- `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/IAuditableEntity.cs`

### Core Layer (12 files)
- `Backend/Shared/adessoGPT.Core/Audit/IAuditService.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditService.cs` (561 lines)
- `Backend/Shared/adessoGPT.Core/Audit/IAuditEntityConfiguration.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditEntityConfigurationBuilder.cs` (667 lines)
- `Backend/Shared/adessoGPT.Core/Audit/AuditCollectionBuilder.cs` (103 lines)
- `Backend/Shared/adessoGPT.Core/Audit/CollectionDiffEngine.cs` (519 lines)
- `Backend/Shared/adessoGPT.Core/Audit/AuditMetadata.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditDifference.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditDifferenceDisplay.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditCollectionMetadata.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditedEntityTypeInfo.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditIgnoreAttribute.cs`
- `Backend/Shared/adessoGPT.Core/Audit/AuditServiceRegistrationExtensions.cs`

### Application Layer (8 files)
- `Backend/Application/adessoGPT.Application.ControlCenter/Business/Audit/ConfigurationAuditEndpoints.cs`
- `Backend/Application/.../Audit/GetAudits/GetConfigurationAuditQuery.cs`
- `Backend/Application/.../Audit/GetAudits/GetConfigurationAuditQueryHandler.cs`
- `Backend/Application/.../Audit/GetAudits/GetConfigurationAuditQueryResponse.cs`
- `Backend/Application/.../Audit/GetAudits/GetConfigurationAuditQueryValidator.cs`
- `Backend/Application/.../Audit/GetAuditTypes/GetAuditEntityTypesQuery.cs`
- `Backend/Application/.../Audit/GetAuditTypes/GetAuditEntityTypesQueryHandler.cs`
- `Backend/Application/.../Audit/GetAuditTypes/GetAuditEntityTypesQueryResponse.cs`

### Infrastructure Layer (4 files)
- `Backend/Infrastructure/adessoGPT.Infrastructure.Persistence/Interceptors/ConfigurationAuditInterceptor.cs`
- `Backend/Infrastructure/.../Persistence.InMemory/Configurations/System/ConfigurationAuditEntryConfiguration.cs`
- `Backend/Infrastructure/.../Persistence.CosmosDb/Configurations/System/ConfigurationAuditEntryConfiguration.cs`
- `Backend/Infrastructure/.../Persistence.MongoDb/Configurations/System/ConfigurationAuditEntryConfiguration.cs`

### Tests (3 files)
- `Backend/Tests/Application/adessoGPT.Application.Tests/Audit/AuditSensitivePropertyTests.cs`
- `Backend/Tests/Application/adessoGPT.Application.Tests/Audit/AuditCollectionAutoDetectionTests.cs`
- `Backend/Tests/Application/adessoGPT.Application.Tests/Audit/CollectionDiffEngineTests.cs`

### Audited Entity Configurations (27 entities with IAuditEntityConfiguration<T>)
Located as inner classes within their domain entity files in `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/`.

**Total: ~31 implementation files + 27 entity configuration classes + 3 test files**

---

## 9. DI Registration

```csharp
// CoreModule.cs — singleton
services.AddSingleton<IDisplayInfoService, DisplayInfoService>();
services.AddAuditServices(scanningAssemblies);  // -> IAuditService singleton

// DependencyInjectionRegistrations.cs — scoped (needs user context)
services.AddScoped<ConfigurationAuditInterceptor>();
// Interceptor added to DbContext via options.AddInterceptors(...)
```

---

## 10. Key Design Decisions

1. **Synchronous interceptor** (not async event / domain event): Audit entries are created in the same transaction as the entity change. No eventual consistency risk.
2. **Configuration-changes only scope**: Only `ISystemSetting` entities are audited. User activity, authentication events, and data access are NOT audited.
3. **No feature flag**: Audit is always enabled. Cannot be toggled at runtime.
4. **String-based EntityType**: Stored as `type.Name` (not fully qualified). Resolved back via domain assembly reflection at query time.
5. **JSON-serialized values**: Old/new values stored as JSON strings. Display layer deserializes as needed.
6. **Partition strategy**: Audit entries use a dedicated "Audit" partition scope in Cosmos DB / MongoDB.
