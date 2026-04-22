# Plan: CQRS-Struktur für Budget-Feature (Queries + Commands)

## Context

UserBudgetState existiert als Domain-Entity mit DB-Konfigurationen. Es fehlt die CQRS-Struktur.

**Placement-Analyse:** Im Projekt werden 13 Features zwischen ControlCenter (Admin-CRUD, Reports) und Application (User-Reads, Chat-Flow) aufgeteilt. Budget folgt demselben Pattern:
- **Application/Business/Budget/** — User-facing Queries + interne Chat-Flow Commands
- **ControlCenter/Business/Budget/** — Admin-Reports

## Scope

Komplette CQRS-Skelett-Struktur für alle Budget-Operationen. Grobe Handler-Implementierung. Noch keine Cosmos-Patch-Operationen, kein Tier-Resolver, keine Chat-Flow-Integration.

## Änderungen

### 1. IUserDbContext erweitern
**Datei:** `Shared/adessoGPT.Domain/IUserDbContext.cs`
- `DbSet<UserBudgetState> BudgetStates { get; }` hinzufügen

### 2. DbSet in Basisklasse registrieren
**Datei:** `Infrastructure/adessoGPT.Infrastructure.Persistence/AdessoGptCosmosDbContext.cs` (enthält `AdessoGptDbContextBase<T>`)
- `DbSet<UserBudgetState> BudgetStates { get; set; }` hinzufügen

### 3. Feature-Ordner (zwei Projekte)

**Application/adessoGPT.Application/Business/Budget/** (User + Chat-Flow):
```
Budget/
├── BudgetEndpoints.cs                          # IEndpointMapper, /api/budget/...
├── GetBudgetState/
│   ├── GetBudgetStateQuery.cs
│   ├── GetBudgetStateQueryHandler.cs
│   ├── GetBudgetStateQueryValidator.cs
│   └── GetBudgetStateQueryResponse.cs
├── EnsureBudgetState/
│   ├── EnsureBudgetStateCommand.cs
│   ├── EnsureBudgetStateCommandHandler.cs
│   └── EnsureBudgetStateCommandValidator.cs
└── RecordBudgetUsage/
    ├── RecordBudgetUsageCommand.cs
    ├── RecordBudgetUsageCommandHandler.cs
    └── RecordBudgetUsageCommandValidator.cs
```

**Application/adessoGPT.Application.ControlCenter/Business/Budget/** (Admin-Reports):
```
Budget/
├── BudgetAdminEndpoints.cs                     # IEndpointMapper, /api/control-center/budget/...
└── GetBudgetUsageReport/
    ├── GetBudgetUsageReportQuery.cs
    ├── GetBudgetUsageReportQueryHandler.cs
    ├── GetBudgetUsageReportQueryValidator.cs
    └── GetBudgetUsageReportQueryResponse.cs
```

### 4. Queries (Read-Seite)

#### GetBudgetStateQuery (Application)
- `IQuery<GetBudgetStateQueryResponse>`
- Felder: `required BudgetPeriod Period`
- Handler: Berechnet deterministische ID via `UserBudgetStateId.ForPeriod()`, Point-Read gegen `_userDbContext.BudgetStates`. Nicht gefunden → `NotFoundError`. Gefunden → Response mappen.
- Response: `UserBudgetStateId Id`, `BudgetPeriod Period`, `DateTimeOffset PeriodStart`, `DateTimeOffset PeriodEnd`, `long TokensUsed`, `decimal CostUsd`, `int RequestCount`, `DateTimeOffset? LastRecordedAt`
- Namespace: `adessoGPT.Application.Business.Budget.GetBudgetState`

#### GetBudgetUsageReportQuery (ControlCenter)
- `IQuery<GetBudgetUsageReportQueryResponse>`
- Felder: `BudgetPeriod? Period`, `DateTimeOffset? FromDate`, `DateTimeOffset? ToDate`, `int PageNumber = 1`, `int PageSize = 25`
- Handler: Listet UserBudgetState-Dokumente mit optionalen Filtern, Pagination analog `GetConfigurationAuditQuery` (Count, Skip, Take, TotalPages).
- Response: `BudgetUsageEntryDto[]`, `int TotalCount`, `int PageNumber`, `int PageSize`, `int TotalPages`
- Namespace: `adessoGPT.Application.ControlCenter.Business.Budget.GetBudgetUsageReport`

### 5. Commands (Write-Seite, beide in Application)

#### EnsureBudgetStateCommand
- `ICommand` (kein Rückgabewert)
- Felder: `required BudgetPeriod Period`
- Handler: Berechnet deterministische ID, prüft ob Dokument existiert. Nein → `UserBudgetState.Create()` + Add + SaveChanges. Ja → no-op. UserId automatisch via Interceptor.
- Namespace: `adessoGPT.Application.Business.Budget.EnsureBudgetState`

#### RecordBudgetUsageCommand
- `ICommand` (kein Rückgabewert)
- Felder: `required UserBudgetStateId BudgetStateId`, `required long TokensUsed`, `required decimal CostUsd`
- Handler: Lädt BudgetState per ID, inkrementiert Counter (TokensUsed += , CostUsd += , RequestCount++, LastRecordedAt = now), SaveChanges.
- Später: wird durch Cosmos Patch-Increment für Atomarität ersetzt.
- Namespace: `adessoGPT.Application.Business.Budget.RecordBudgetUsage`

### 6. Endpoints (zwei Endpoint-Klassen)

**BudgetEndpoints** (Application) — `/api/budget`:
- `GetBudgetStateQuery` → `GET /api/budget/state` (authentifizierter User)
- EnsureBudgetState und RecordBudgetUsage sind interne Commands (kein Endpoint — MediatR-Aufruf aus Chat-Flow).

**BudgetAdminEndpoints** (ControlCenter) — `/api/control-center/budget`:
- `GetBudgetUsageReportQuery` → `GET /api/control-center/budget/report` (RequireRole ControlCenterAdmin)

## Referenz-Dateien

| Pattern | Datei |
|---------|-------|
| User-Query + Handler (Application) | `Application/Business/Conversations/GetConversations/GetConversations*.cs` |
| Admin-Query + Handler (ControlCenter) | `ControlCenter/Business/Audit/GetAudits/GetConfigurationAudit*.cs` |
| User-Endpoint (Application) | `Application/Business/Conversations/ConversationEndpoints.cs` |
| Admin-Endpoint (ControlCenter) | `ControlCenter/Business/Audit/ConfigurationAuditEndpoints.cs` |
| IUserDbContext | `Shared/adessoGPT.Domain/IUserDbContext.cs` |
| DbContextBase | `Infrastructure/Persistence/AdessoGptCosmosDbContext.cs` (Zeile 24ff) |
| UserBudgetState Entity | `Shared/adessoGPT.Domain/PersistedEntities/Budget/UserBudgetState.cs` |
| ICommand/IQuery | `Shared/adessoGPT.Core/CQRS/ICommand.cs`, `IQuery.cs` |

## Verifikation

1. `dotnet build /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/adessoGPT.sln` — keine Compile-Fehler
2. CQRS-Konventionen: Handler + Validator `internal`, Command + Query + Response `public`
3. Namespace-Konsistenz:
   - Application-Handler: `adessoGPT.Application.Business.Budget.*`
   - ControlCenter-Handler: `adessoGPT.Application.ControlCenter.Business.Budget.*`
