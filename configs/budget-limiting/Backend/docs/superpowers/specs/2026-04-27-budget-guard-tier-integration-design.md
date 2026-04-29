# Budget Guard — Tier-Based Limit Enforcement

## Summary

Integrate `IBudgetTierResolver` into `BudgetGuardService` so that per-user budget enforcement uses the resolved `BudgetTier`'s daily/weekly/monthly token limits instead of the global `BudgetLimitSettings.MonthlyTokenLimit`.

## Scope

- Token limit enforcement (daily, weekly, monthly) from the resolved `BudgetTier`
- Out of scope: `RequestsPerMinute` rate limiting, `SoftWarningPercent` warning threshold

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Caching strategy | Direct resolver usage | `BudgetTierRepository` and `UserGroupRepository` are already FusionCache-backed. No extra cache layer needed. |
| Period enforcement | All non-null limits enforced | If a tier configures daily AND monthly limits, both are checked. Any exceeded period triggers fallback/block. |
| No-tier behavior | Unlimited access | If no tier resolves for a user (no group match, no default tier), budget enforcement is skipped entirely. |
| Global MonthlyTokenLimit | Not used for per-user enforcement | `BudgetLimitSettings.MonthlyTokenLimit` is a company-wide reference metric. Per-user limits come exclusively from tiers. `IsEnabled` remains the global on/off switch. |
| State creation | Lazy / read-only guard | Missing `UserBudgetState` documents are treated as 0 usage. State creation happens when usage is recorded, not during the check. |
| Expired period handling | Treated as 0 usage | If `UserBudgetState.PeriodEnd < UtcNow`, the period has rolled over — treat as fresh period with 0 usage. |

## Modified CheckBudgetAsync Flow

```
1. Load BudgetLimitSettings
   └─ !IsEnabled → return Allowed

2. Call IBudgetTierResolver.ResolveForUserAsync()
   └─ null (no tier) → return Allowed (unlimited)

3. Build period checks from resolved tier's non-null limits:
   ├─ DailyTokenLimit   → load UserBudgetState("budget-daily")
   ├─ WeeklyTokenLimit  → load UserBudgetState("budget-weekly")
   └─ MonthlyTokenLimit → load UserBudgetState("budget-monthly")

4. For each configured period:
   ├─ state is null → 0 usage → OK
   ├─ state.PeriodEnd < UtcNow → expired → 0 usage → OK
   └─ state.TokensUsed >= limit → EXCEEDED

5. Any period exceeded?
   ├─ Yes → proceed to fallback/block logic (unchanged)
   └─ No  → return Allowed
```

## Changes to BudgetGuardService

### New Dependency

```csharp
private readonly IBudgetTierResolver _budgetTierResolver;
```

Added to constructor injection. No other new dependencies.

### Modified Method: CheckBudgetAsync

Replace the current global-limit check with:

1. Early return if `!settings.IsEnabled`
2. Resolve tier via `_budgetTierResolver.ResolveForUserAsync()`
3. If no tier → return `Allowed`
4. For each non-null period limit on the tier, query `UserBudgetState` from `_dbContext.BudgetStates`
5. If any period's `TokensUsed >= limit` (and state is not expired), proceed to existing fallback/block logic

### Unchanged

- `EnforceBudgetAsync` — no changes, it delegates to `CheckBudgetAsync`
- `BudgetCheckResult` — no new fields
- `BudgetCheckOutcome` enum — no new values
- Fallback model resolution logic — stays identical

## File Inventory

| File | Change |
|---|---|
| `Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs` | Inject `IBudgetTierResolver`, rewrite `CheckBudgetAsync` |
| No new files | — |

## DB Query Impact

Up to 3 `UserBudgetState` reads per `CheckBudgetAsync` call (only for periods with non-null limits on the resolved tier). These are small per-user documents from the user partition — indexed by ID, fast lookups. The tier resolution itself hits FusionCache (no DB call on cache hit).
