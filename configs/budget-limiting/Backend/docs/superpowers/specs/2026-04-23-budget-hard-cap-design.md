# Budget Hard Cap — Design Spec

**Date:** 2026-04-23
**PBI:** 3271 (Budget Limits)
**Branch:** feature/PBI3271_Budget_Limits
**Status:** Approved design, ready for implementation plan

## Problem

Budget usage is recorded in `UserBudgetState` (daily/weekly/monthly) after each chat completes, but nothing prevents a user from exceeding their budget. The recording happens in the `ChatStreamPersistingWrapper` — too deep in the pipeline, after tokens have already been consumed.

## Goal

Add a hard cap that checks budget **before** the LLM call. When exceeded, either switch to a free fallback model or block the request. All users get a fixed monthly token cap. Free/fallback models can be used without limit.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Integration point | `CreateChatStreamQueryHandler` (before runtime factory) | Full ChatStreamContext available, single gateway before LLM call |
| Cap source | Hardcoded constant (`100_000` tokens/month) | Tier resolution (Entra groups) comes later |
| Fallback model | `IsBudgetFallback` flag on `AgentModelConfiguration` | Admin controls per-agent which model is the fallback. No fallback = block. |
| Unlimited support | Fallback model has unlimited usage | When user is already on the fallback model, budget check returns `Allowed` |
| Model switch mechanism | `UpdateConversationModelCommand` + re-run `CreateChatStreamContextQuery` | Uses existing commands, no new properties on context, read-only context query is safe to call twice |
| Localization | `LocalizedString.For(ErrorMessages.*)` | Consistent with existing error/warning patterns |
| Period rollover edge case | Acceptable: first request of new month may briefly see stale data | Next `RecordChatBudgetUsage` triggers rollover, second request is correct |

## Architecture

### Flow (Standard Chat)

```
StartChatConversationCommandHandler:
  1. CreateConversationCommand             -> Conversation + Message persisted
  2. CreateChatStreamContextQuery          -> Context assembled (read-only)
  3. IBudgetGuardService.CheckBudgetAsync(context)
     |
     |-- Allowed          -> continue to step 6
     |-- FallbackModel    -> step 4 + 5, then continue to step 6
     |-- Blocked          -> return ChatBudgetExhaustedResponse, stop
     |
  4. UpdateConversationModelCommand        -> Persist fallback ModelId
  5. CreateChatStreamContextQuery          -> Rebuild context with fallback model
  6. CreateChatStreamQuery                 -> LLM call with (possibly switched) model
```

For Resume/Regenerate: steps 1 is skipped (conversation already exists), steps 2-6 are identical.

For Realtime: same pattern in `CreateRealtimeChatStreamQueryHandler`.

### IBudgetGuardService

```csharp
public enum BudgetCheckOutcome
{
    Allowed,
    FallbackModel,
    Blocked,
}

public record BudgetCheckResult
{
    public required BudgetCheckOutcome Outcome { get; init; }
    public ModelOptionsId? OriginalModelOptionsId { get; init; }
    public ModelOptionsId? FallbackModelOptionsId { get; init; }
}

public interface IBudgetGuardService
{
    Task<BudgetCheckResult> CheckBudgetAsync(
        ChatStreamContext context,
        CancellationToken cancellationToken
    );
}
```

### Service Logic

```
CheckBudgetAsync(context):
  1. Read UserBudgetState for "budget-monthly" (via IUserDbContext)
  2. If state is null or TokensUsed < MonthlyTokenCap -> Allowed
  3. If current model IS the fallback model -> Allowed (unlimited)
  4. Find IsBudgetFallback model in agent's ModelConfigurations
     - Found -> FallbackModel (with OriginalModelOptionsId + FallbackModelOptionsId)
     - Not found -> Blocked
```

Hardcoded cap: `private const long MonthlyTokenCap = 100_000;`

### ChatStreamResponse Types

```csharp
public record ChatBudgetWarningResponse : ChatStreamResponse
{
    public ChatBudgetWarningResponse() : base("budget_warning") { }
    public required string Message { get; init; }
    public required string FallbackModelTitle { get; init; }
}

public record ChatBudgetExhaustedResponse : ChatStreamResponse
{
    public ChatBudgetExhaustedResponse() : base("budget_exhausted") { }
    public required string Message { get; init; }
}
```

Messages are localized via `ErrorMessages` resource files.

### AgentModelConfiguration Change

```csharp
public class AgentModelConfiguration
{
    public required ModelOptionsId ModelOptionsId { get; init; }
    public string? SystemMessage { get; init; }
    public bool IsDefault { get; init; }
    public bool IsBudgetFallback { get; init; }  // NEW
}
```

At most one model per agent should have `IsBudgetFallback = true`. If multiple are set, the service takes the first match. Initially hardcoded in seed data.

### Localization Keys

| Key | EN | DE |
|-----|----|----|
| `Budget_Exhausted_Message` | Your monthly budget has been exhausted. | Ihr monatliches Budget ist aufgebraucht. |
| `Budget_FallbackModel_Warning` | Budget exceeded. Switched to {0}. | Budget überschritten. Gewechselt auf {0}. |

## Files to Create

| File | Purpose |
|------|---------|
| `Application/Business/Budget/Services/IBudgetGuardService.cs` | Interface |
| `Application/Business/Budget/Services/BudgetGuardService.cs` | Implementation with hardcoded cap |

## Files to Modify

| File | Change |
|------|--------|
| `Domain/Entities/Agent/AgentModelConfiguration.cs` (or equivalent) | Add `IsBudgetFallback` property |
| `Application/Business/Chat/ChatStreaming/CreateChatStream/CreateChatStreamQueryHandler.cs` | Add budget check before runtime creation |
| `Application.Realtime/.../CreateRealtimeChatStreamQueryHandler.cs` (if separate) | Same budget check |
| `Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs` | New response type |
| `Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs` | New response type |
| `Application/Localization/ErrorMessages.resx` + `.de.resx` | Budget message keys |
| `Application/ApplicationModule.cs` | Register IBudgetGuardService |
| Seed data / configuration | Set `IsBudgetFallback` on appropriate models |

## Not In Scope

- 80% warning thresholds / UI endpoints for budget status banners
- BudgetTier entity and Entra group tier resolution
- ModelPricing / CostUsd calculation (stays 0m dummy)
- Control Center UI for IsBudgetFallback configuration
- AI pipeline budgeting
- Feature flag for budget enforcement (enforcement is always on)
