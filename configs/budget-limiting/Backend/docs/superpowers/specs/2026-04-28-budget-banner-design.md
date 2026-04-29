# Budget Banner via SSE — Design

**Date:** 2026-04-28
**Branch:** feature/PBI3271_Budget_Limits
**Related research:** `../2026-04-27-budget-banner-sse-research.md`

## Goal

Notify users in-app when their budget consumption crosses a soft warning threshold (e.g. 80%) or reaches the hard limit (100%). Surface the relevant percentage and, when applicable, the fallback model that takes over after the hard limit.

## Scope

- Server-side: extend `BudgetGuardService` with an `Approaching` outcome, replace the two existing `budget_warning` / `budget_exhausted` SSE events with one unified `budget_status` event.
- Client-side: handle the new event in the chat stream dispatchers (standard + realtime), introduce a `BudgetBannerStore`, render a banner in the app shell.

Out of scope:
- Persistent banner visibility outside an active chat send (no pull endpoint, no app-start banner).
- Per-tier custom warning messaging (uses i18n templates only).
- Backend persistence of "already-notified" state — banner re-fires on every send above threshold; dismiss is a UI concern.

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | When multiple periods are above threshold, the **highest percentage** wins. | Surfaces the most pressing limit; user-facing simplicity. |
| D2 | **Single SSE event** `budget_status` with `Severity` discriminator (replaces `budget_warning`, `budget_exhausted`). | Branch unreleased; avoids three parallel event types. Fallback model action is internal — banner is pure display. |
| D3 | Soft warning threshold lives on `BudgetTier.SoftWarningPercent` (already exists, `int?`). | Per-tier configuration via existing entity field. |
| D4 | `SoftWarningPercent = null` ⇒ **no Approaching event** for that tier. | Nullable = explicit opt-out, consistent with nullable token-limit semantics ("unlimited"). |
| D5 | Backend stays **stateless**: event fires on every send above threshold. Throttling is a frontend concern. | Backend simplicity; idempotent event semantics. |

## Architecture

### Flow

```
Chat-Send Handler
  └─> BudgetGuardService.EnforceBudgetAsync(context, conversationId, rebuild, ct)
        ├─> IBudgetTierResolver.ResolveForUserAsync(ct) → BudgetTier?
        ├─> EvaluatePeriodsAsync(tier, ct):
        │     for each (period, limit) in [(Daily, tier.DailyTokenLimit),
        │                                   (Weekly, tier.WeeklyTokenLimit),
        │                                   (Monthly, tier.MonthlyTokenLimit)]:
        │       if limit is null or limit == 0: skip
        │       state ← UserBudgetState for current user, period
        │       pct ← (state?.TokensUsed ?? 0) * 100 / limit
        │       collect (period, pct)
        │     return (maxPct, periodOfMax) or (0, default) if empty
        ├─> Severity decision:
        │     - maxPct ≥ 100 && agent has IsBudgetFallback model → FallbackModel
        │     - maxPct ≥ 100 && no fallback                       → Blocked
        │     - tier.SoftWarningPercent is not null
        │       && maxPct ≥ tier.SoftWarningPercent              → Approaching
        │     - else                                              → Allowed
        └─> Publish ChatBudgetStatusResponse when Outcome ≠ Allowed:
              - Approaching → Severity = Approaching, FallbackModelTitle = null
              - FallbackModel → Severity = Warning,    FallbackModelTitle = <new model title>
                                + UpdateConversationModelCommand + rebuild context
              - Blocked     → Severity = Exhausted,   yield break
```

### Backend changes

**New file: `Backend/Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetStatusResponse.cs`**

```csharp
namespace adessoGPT.Chat.Abstractions.Streaming.Updates;

public sealed record ChatBudgetStatusResponse : ChatStreamResponse
{
    public override string Event => "budget_status";

    public required BudgetStatusSeverity Severity { get; init; }
    public required int Percentage { get; init; }
    public required BudgetPeriod Period { get; init; }
    public string? FallbackModelTitle { get; init; }
}

public enum BudgetStatusSeverity
{
    Approaching = 0,
    Warning = 1,
    Exhausted = 2,
}
```

Register in the polymorphic `ChatStreamResponse` JSON converter alongside existing event types.

**Removed files:**
- `ChatBudgetWarningResponse.cs`
- `ChatBudgetExhaustedResponse.cs`

**Updated: `Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`**

- `BudgetCheckOutcome` enum gains `Approaching`.
- `BudgetCheckResult` gains `Percentage` (int), `Period` (BudgetPeriod), `FallbackModelTitle` (string?).
- `IsAnyPeriodExceededAsync` → renamed to `EvaluatePeriodsAsync`, returns `(int MaxPercentage, BudgetPeriod Period)`. Skips periods where the tier limit is null or zero.
- `CheckBudgetAsync` applies the severity decision tree above.
- `EnforceBudgetAsync` publishes `ChatBudgetStatusResponse` for Approaching / FallbackModel / Blocked. The Blocked path keeps `yield break`.

### Frontend changes

**New store: `Frontend/adessoGPT.Web/libs/chat/src/features/budget-banner/budget-banner.store.ts`**

```ts
type BudgetBannerStatus = {
  severity: 'Approaching' | 'Warning' | 'Exhausted';
  percentage: number;
  period: 'Daily' | 'Weekly' | 'Monthly';
  fallbackModelTitle: string | null;
};

// Signal store with:
//   state:    currentStatus: BudgetBannerStatus | null
//             dismissedSeverities: Set<Severity>
//   methods:  setStatus(status)   — no-op if severity already dismissed
//             dismiss()           — clears currentStatus, adds severity to dismissedSeverities
//   no persistence — reload resets the store.
```

**Dispatch updates:**
- `libs/chat/src/features/chat/existing-chat/chat-stream.store.ts` — add `case 'budget_status'` calling `budgetBannerStore.setStatus(...)`.
- `libs/chat/src/features/chat/realtime/realtime.store.ts` — same.

**Banner component:** rendered in the app shell (or chat layout), bound to `currentStatus`. Dismiss button calls `dismiss()`. Severity → color (Approaching/Warning = warn, Exhausted = error).

**i18n keys** (en/de) for three message templates with `{period}` and `{percentage}` (and `{fallbackModelTitle}` for Warning). Period names localized.

**Removed:** the old `budget_warning` / `budget_exhausted` cases existed only in the `default` branch of the dispatch — no UI dependencies to clean up.

## Error Handling

- `BudgetGuardService` returns `Result<BudgetEnforcementResult>` — no try/catch added; `ErrorPipelineBehavior` covers unexpected exceptions.
- Defensive: limit `0` is treated as "skip period" (FluentValidation should already reject this on `BudgetTier`).
- Frontend store ignores malformed events (missing fields) silently — schema is generated from OpenAPI, runtime mismatches are unexpected.

## Tests

**Backend (`BudgetGuardServiceTests`):**
- Approaching when `SoftWarningPercent = 80` and used ≥ 80%, < 100%.
- Allowed when `SoftWarningPercent = null` even at 90% usage.
- Highest percentage wins across multiple periods over threshold.
- Periods with `null` limit are skipped from percentage evaluation.
- Existing tests adapted to the new `BudgetCheckResult` shape.
- FallbackModel path still publishes `Severity = Warning` with `FallbackModelTitle`.

**Frontend:**
- `budget-banner.store` — `dismiss()` blocks subsequent `setStatus` of same severity; higher severity overrides.
- Banner component renders per severity with correct copy.

## Implementation Order

1. New `ChatBudgetStatusResponse` + enum, register in polymorphic converter.
2. Refactor `BudgetGuardService` (outcome enum, result shape, evaluation, severity logic, publish).
3. Delete old response types, fix references.
4. Backend tests.
5. Regenerate OpenAPI client (`npm run generate:api` per project workflow).
6. Frontend `BudgetBannerStore` + dispatch cases.
7. Banner component + i18n.
8. Frontend tests.
9. `dotnet csharpier format .` + frontend `npm run prettier` + `npm run lint`.

## Rules Update

- Update `Backend/.claude/rules/budget.md` to document `ChatBudgetStatusResponse`, the `Approaching` outcome, and the `SoftWarningPercent = null ⇒ no warning` semantics.
