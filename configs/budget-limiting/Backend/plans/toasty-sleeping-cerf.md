# Plan: CQRS-Struktur für Budget-Feature (Queries + Commands)

## Context

UserBudgetState existiert als Domain-Entity mit DB-Konfigurationen. Es fehlt die CQRS-Struktur. Der User möchte zuerst die **Read-Seite** (Queries) definieren, dann die Write-Seite (Commands) — saubere CQRS-Trennung. Als Referenz dient das Audit-Feature im ControlCenter-Layer (`GetConfigurationAuditQuery`). Alle Budget-Queries und -Commands sollen im `adessoGPT.Application.ControlCenter`-Projekt unter `Business/Budget/` liegen.

## Scope

Komplette CQRS-Skelett-Struktur für alle Budget-Operationen. Grobe Handler-Implementierung. Noch keine Cosmos-Patch-Operationen, kein Tier-Resolver, keine Chat-Flow-Integration.

## Änderungen

### 0. Hooks & Permissions aus Projekt-settings übernehmen
**Datei:** `configs/budget-limiting/Backend/settings.json`
**Quelle:** `app/.claude/settings.local.json`

Merge:
- **PreToolUse-Hook** (pre-commit format check): Neuer Eintrag im bestehenden PreToolUse-Array neben worktree_guard. Matcher `Bash`, gated mit `if: "Bash(git commit*)"`, ruft `$CLAUDE_PROJECT_DIR/.claude/hooks/pre-commit-format.sh` auf.
- **Permissions-Block**: 67 Allow-Regeln (Bash-Befehle, MCP-Tools, WebFetch-Domains, etc.) + `defaultMode: "acceptEdits"`.
- Bestehende Einstellungen (model, hooks, plugins, extraKnownMarketplaces) bleiben erhalten.

### 1. IUserDbContext erweitern
**Datei:** `Shared/adessoGPT.Domain/IUserDbContext.cs`
- `DbSet<UserBudgetState> BudgetStates { get; }` hinzufügen

### 2. DbSet in Basisklasse registrieren
**Datei:** `Infrastructure/adessoGPT.Infrastructure.Persistence/AdessoGptCosmosDbContext.cs` (enthält `AdessoGptDbContextBase<T>`)
- `DbSet<UserBudgetState> BudgetStates { get; set; }` hinzufügen

### 3. Feature-Ordner + Endpoint
**Pfad:** `Application/adessoGPT.Application.ControlCenter/Business/Budget/`

```
Budget/
├── BudgetEndpoints.cs                          # IEndpointMapper, /api/budget/...
├── GetBudgetState/
│   ├── GetBudgetStateQuery.cs
│   ├── GetBudgetStateQueryHandler.cs
│   ├── GetBudgetStateQueryValidator.cs
│   └── GetBudgetStateQueryResponse.cs
├── GetBudgetUsageReport/
│   ├── GetBudgetUsageReportQuery.cs
│   ├── GetBudgetUsageReportQueryHandler.cs
��   ├── GetBudgetUsageReportQueryValidator.cs
│   └── GetBudgetUsageReportQueryResponse.cs
├── EnsureBudgetState/
│   ├── EnsureBudgetStateCommand.cs
│   ├── EnsureBudgetStateCommandHandler.cs
│   └── EnsureBudgetStateCommandValidator.cs
└── RecordBudgetUsage/
    ├── RecordBudgetUsageCommand.cs
    ├── RecordBudgetUsageCommandHandler.cs
    └── RecordBudgetUsageCommandValidator.cs
```

### 4. Queries (Read-Seite)

#### GetBudgetStateQuery
- `IQuery<GetBudgetStateQueryResponse>`
- Felder: `required BudgetPeriod Period`
- Handler: Berechnet deterministische ID via `UserBudgetStateId.ForPeriod()`, Point-Read gegen `_userDbContext.BudgetStates`. Nicht gefunden → `NotFoundError`. Gefunden → Response mappen.
- Response: `UserBudgetStateId Id`, `BudgetPeriod Period`, `DateTimeOffset PeriodStart`, `DateTimeOffset PeriodEnd`, `long TokensUsed`, `decimal CostUsd`, `int RequestCount`, `DateTimeOffset? LastRecordedAt`
- Pattern: Wie `GetConfigurationAuditQuery` — reine Leseabfrage, Validator prüft Eingaben.

#### GetBudgetUsageReportQuery
- `IQuery<GetBudgetUsageReportQueryResponse>`
- Felder: `BudgetPeriod? Period`, `DateTimeOffset? FromDate`, `DateTimeOffset? ToDate`, `int PageNumber = 1`, `int PageSize = 25`
- Handler: Listet UserBudgetState-Dokumente mit optionalen Filtern, Pagination analog `GetConfigurationAuditQuery` (Count, Skip, Take, TotalPages).
- Response: `BudgetUsageEntryDto[]`, `int TotalCount`, `int PageNumber`, `int PageSize`, `int TotalPages`
- Admin-Query mit `RequireRole(ControlCenterAdmin)`.

### 5. Commands (Write-Seite)

#### EnsureBudgetStateCommand
- `ICommand` (kein Rückgabewert)
- Felder: `required BudgetPeriod Period`
- Handler: Berechnet deterministische ID, prüft ob Dokument existiert. Nein → `UserBudgetState.Create()` + Add + SaveChanges. Ja → no-op. UserId automatisch via Interceptor.

#### RecordBudgetUsageCommand
- `ICommand` (kein Rückgabewert)
- Felder: `required UserBudgetStateId BudgetStateId`, `required long TokensUsed`, `required decimal CostUsd`
- Handler: Lädt BudgetState per ID, inkrementiert Counter (TokensUsed += , CostUsd += , RequestCount++, LastRecordedAt = now), SaveChanges.
- Später: wird durch Cosmos Patch-Increment für Atomarität ersetzt.

### 6. BudgetEndpoints
- `IEndpointMapper` nach dem `ConfigurationAuditEndpoints`-Pattern
- Route-Gruppe: `/api/budget`
- `GetBudgetStateQuery` → `GET /api/budget/state` (authentifizierter User)
- `GetBudgetUsageReportQuery` → `GET /api/budget/report` (Admin)
- EnsureBudgetState und RecordBudgetUsage sind interne Commands (kein öffentlicher Endpoint — werden von anderen Handlern via MediatR aufgerufen).

## Referenz-Dateien

| Pattern | Datei |
|---------|-------|
| Query + Handler + Validator + Response | `ControlCenter/Business/Audit/GetAudits/GetConfigurationAudit*.cs` |
| Endpoint-Registrierung | `ControlCenter/Business/Audit/ConfigurationAuditEndpoints.cs` |
| IUserDbContext | `Shared/adessoGPT.Domain/IUserDbContext.cs` |
| DbContextBase | `Infrastructure/Persistence/AdessoGptCosmosDbContext.cs` (Zeile 24ff) |
| UserBudgetState Entity | `Shared/adessoGPT.Domain/PersistedEntities/Budget/UserBudgetState.cs` |
| ICommand/IQuery | `Shared/adessoGPT.Core/CQRS/ICommand.cs`, `IQuery.cs` |

## Verifikation

1. `dotnet build /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/adessoGPT.sln` — keine Compile-Fehler
2. CQRS-Konventionen: Handler + Validator `internal`, Command + Query + Response `public`
3. Namespace-Konsistenz: `adessoGPT.Application.ControlCenter.Business.Budget.*`
