# Plan: Budget-Query-Verbesserungen — Admin-Bug-Fix, Limit-Info, All-Periods-Endpoint

## Context

Die Budget-UI (Admin + User) braucht bessere Backend-Daten. Drei Probleme:
1. **Bug:** `GetBudgetUsageReportQueryHandler` nutzt `IUserDbContext` — Admins sehen nur eigene Daten statt aller User
2. **Fehlende Limit-Info:** `GetBudgetStateQueryResponse` liefert nur `TokensUsed` ohne den Cap — Frontend kann keinen Fortschrittsbalken rendern
3. **Unpraktisch:** User muss 3 separate API-Calls machen um alle Perioden (Daily/Weekly/Monthly) zu sehen

## Steps

### 1. Fix Admin-Report: IgnoreQueryFilters

**File:** `Application/adessoGPT.Application.ControlCenter/Business/Budget/GetBudgetUsageReport/GetBudgetUsageReportQueryHandler.cs`

Add `.IgnoreQueryFilters()` to the BudgetStates query — established pattern used in `DeleteExpiredConversationsCommandHandler`, `GetConversationsInDateRangeQueryHandler` etc.

```csharp
var budgetStatesQuery = _dbContext.BudgetStates.IgnoreQueryFilters().AsNoTracking().AsQueryable();
```

No DbContext change needed — `IUserDbContext` bleibt, nur der Query wird ungefiltert.

### 2. Add MonthlyTokenLimit to BudgetLimitSettings

**File:** `Shared/adessoGPT.Domain/PersistedEntities/System/SingleSettings/BudgetLimitSettings.cs`

Add a `MonthlyTokenLimit` property (nullable `long?`, CLR default = null = no limit). The `BudgetGuardService` reads this instead of the hardcoded `MonthlyTokenCap = 500` constant.

```csharp
[DisplayInfo(...)]
public required long? MonthlyTokenLimit { get; init; }
```

Default: `new() { IsEnabled = true, MonthlyTokenLimit = 500 }` (matches current behavior).

Rules from `persistence.md`: `long?` is correct since the meaningful default (500) differs from CLR default (0).

**EntityMessages:** Add 2 new entries (`BudgetLimitSettings_MonthlyTokenLimit`, `BudgetLimitSettings_MonthlyTokenLimit_Description`) to `.resx`, `.de.resx`, and `.Designer.cs`.

### 3. Update BudgetGuardService to use configurable limit

**File:** `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`

- Remove `private const long MonthlyTokenCap = 500;`
- In `CheckBudgetAsync`: settings are already read — use `settings.MonthlyTokenLimit ?? long.MaxValue` as the cap
- If `MonthlyTokenLimit` is null → no cap → always Allowed (after the IsEnabled check)

### 4. Extend GetBudgetStateQueryResponse with limit info

**File:** `Application/adessoGPT.Application/Business/Budget/GetBudgetState/GetBudgetStateQueryResponse.cs`

Add fields so the frontend can render a progress bar:

```csharp
public long? MonthlyTokenLimit { get; init; }
public bool IsEnabled { get; init; }
```

**File:** `Application/adessoGPT.Application/Business/Budget/GetBudgetState/GetBudgetStateQueryHandler.cs`

- Inject `ISingleSettingsRepository`
- Read `BudgetLimitSettings` and populate the new response fields

### 5. New endpoint: Get all periods at once

**New CQRS feature:** `GetBudgetOverview`

Create a new query `GetBudgetOverviewQuery` (no parameters) that returns all 3 periods in one response, plus the limit info.

**Files to create:**
- `Application/adessoGPT.Application/Business/Budget/GetBudgetOverview/GetBudgetOverviewQuery.cs`
- `Application/adessoGPT.Application/Business/Budget/GetBudgetOverview/GetBudgetOverviewQueryResponse.cs`
- `Application/adessoGPT.Application/Business/Budget/GetBudgetOverview/GetBudgetOverviewQueryHandler.cs`

**Response shape:**
```csharp
public record GetBudgetOverviewQueryResponse
{
    public required bool IsEnabled { get; init; }
    public required long? MonthlyTokenLimit { get; init; }
    public required BudgetPeriodSummary? Daily { get; init; }
    public required BudgetPeriodSummary? Weekly { get; init; }
    public required BudgetPeriodSummary? Monthly { get; init; }
}

public record BudgetPeriodSummary
{
    public required DateTimeOffset PeriodStart { get; init; }
    public required DateTimeOffset PeriodEnd { get; init; }
    public required long TokensUsed { get; init; }
    public required decimal CostUsd { get; init; }
    public required int RequestCount { get; init; }
    public DateTimeOffset? LastRecordedAt { get; init; }
}
```

**Handler:** Read all 3 budget states from `IUserDbContext` + settings from `ISingleSettingsRepository`. Periods without data return `null`.

**Endpoint registration in `BudgetEndpoints.cs`:**
```csharp
group.MapGetCQRS<GetBudgetOverviewQuery, GetBudgetOverviewQueryResponse>("overview");
```
→ `GET /api/budget/overview`

### 6. Build & format verification

```bash
dotnet build /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/adessoGPT.sln
dotnet csharpier format .
```

## Key files

| File | Action |
|------|--------|
| `Application/adessoGPT.Application.ControlCenter/Business/Budget/GetBudgetUsageReport/GetBudgetUsageReportQueryHandler.cs` | EDIT — add IgnoreQueryFilters |
| `Shared/adessoGPT.Domain/PersistedEntities/System/SingleSettings/BudgetLimitSettings.cs` | EDIT — add MonthlyTokenLimit |
| `Shared/adessoGPT.Domain/Localization/EntityMessages.resx` | EDIT — add MonthlyTokenLimit entries |
| `Shared/adessoGPT.Domain/Localization/EntityMessages.de.resx` | EDIT — add MonthlyTokenLimit entries |
| `Shared/adessoGPT.Domain/Localization/EntityMessages.Designer.cs` | EDIT — add MonthlyTokenLimit accessors |
| `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs` | EDIT — use configurable limit |
| `Application/adessoGPT.Application/Business/Budget/GetBudgetState/GetBudgetStateQueryResponse.cs` | EDIT — add limit fields |
| `Application/adessoGPT.Application/Business/Budget/GetBudgetState/GetBudgetStateQueryHandler.cs` | EDIT — inject settings, populate limit |
| `Application/adessoGPT.Application/Business/Budget/GetBudgetOverview/` | CREATE — new query/response/handler |
| `Application/adessoGPT.Application/Business/Budget/BudgetEndpoints.cs` | EDIT — add overview endpoint |
