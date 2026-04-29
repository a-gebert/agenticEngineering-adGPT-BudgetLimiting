# Budget Banner via SSE — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing two budget SSE events with a single `budget_status` event carrying severity (Approaching/Warning/Exhausted), the highest period-percentage and (for the Warning case) the fallback model title.

**Architecture:** A single new SSE event record `ChatBudgetStatusResponse` replaces `ChatBudgetWarningResponse` + `ChatBudgetExhaustedResponse`. `BudgetGuardService` gains an `Approaching` outcome (when `BudgetTier.SoftWarningPercent` is set and the highest period percentage is at/above it but below 100%). The service stays stateless — the event fires on every chat send above the threshold; throttling/dismiss is a frontend concern.

**Tech Stack:** .NET 10, MediatR, EF Core, xUnit + FluentAssertions + NSubstitute. Spec at `configs/budget-limiting/Backend/docs/superpowers/specs/2026-04-28-budget-banner-design.md`. Working directory: `/home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Backend`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetStatusResponse.cs` | New SSE event + `BudgetStatusSeverity` enum |
| Modify | `Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs` | Add `Approaching` to `BudgetCheckOutcome`; add `Percentage` + `Period` to `BudgetCheckResult` |
| Modify | `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs` | Replace `IsAnyPeriodExceededAsync` with `EvaluatePeriodsAsync` returning highest pct/period; severity decision; publish new event |
| Delete | `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs` | Replaced by `ChatBudgetStatusResponse` |
| Delete | `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs` | Replaced by `ChatBudgetStatusResponse` |
| Modify | `Application/adessoGPT.Application/Localization/ErrorMessages.{resx,de.resx,fr.resx,it.resx}` + `.Designer.cs` | Remove `Budget_Exhausted_Message`, `Budget_FallbackModel_Warning` (no longer used; frontend localizes) |
| Modify | `Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs` | Adapt existing assertions to new result shape; add new severity tests |
| Modify | `Backend/.claude/rules/budget.md` | Document new event + Approaching outcome + null-soft-warning semantics |

The polymorphic JSON converter (`PolymorphicSerializeOnlyJsonConverter<ChatStreamResponse>`) discriminates by runtime type — no per-type registration needed for the new event.

---

## Task 1: Add `ChatBudgetStatusResponse` event type

**Files:**
- Create: `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetStatusResponse.cs`

- [ ] **Step 1: Create the new response record + severity enum**

```csharp
namespace adessoGPT.Chat.Abstractions.Streaming.Updates;

using adessoGPT.Domain.PersistedEntities.Budget;

public record ChatBudgetStatusResponse : ChatStreamResponse
{
    public ChatBudgetStatusResponse()
        : base("budget_status") { }

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

- [ ] **Step 2: Verify the abstractions project builds**

Run: `dotnet build Backend/Shared/adessoGPT.Chat.Abstractions`
Expected: `Build succeeded.`

- [ ] **Step 3: Commit**

```bash
git add Backend/Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetStatusResponse.cs
git commit -m "feat: add ChatBudgetStatusResponse SSE event for budget banner"
```

---

## Task 2: Extend `BudgetCheckOutcome` and `BudgetCheckResult`

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs`

- [ ] **Step 1: Add `Approaching` to the outcome enum and extend the result record**

Replace the contents of `IBudgetGuardService.cs` with:

```csharp
namespace adessoGPT.Application.Business.Budget.Services;

using System.Collections.Generic;
using adessoGPT.Chat.Abstractions.Streaming;
using adessoGPT.Core.Results;
using adessoGPT.Domain.PersistedEntities.Budget;
using adessoGPT.Domain.PersistedEntities.System.Settings.ModelOptions;
using adessoGPT.Domain.PersistedEntities.User.Conversation;

public enum BudgetCheckOutcome
{
    Allowed,
    Approaching,
    FallbackModel,
    Blocked,
}

public record BudgetCheckResult
{
    public required BudgetCheckOutcome Outcome { get; init; }
    public int Percentage { get; init; }
    public BudgetPeriod Period { get; init; }
    public ModelOptionsId? OriginalModelOptionsId { get; init; }
    public ModelOptionsId? FallbackModelOptionsId { get; init; }
    public string? FallbackModelTitle { get; init; }
}

public record BudgetEnforcementResult
{
    public bool IsBlocked { get; init; }
    public IAsyncEnumerable<ChatStreamResponse>? BlockedStream { get; init; }
    public ChatStreamContext? EnforcedContext { get; init; }
}

public interface IBudgetGuardService
{
    Task<BudgetCheckResult> CheckBudgetAsync(ChatStreamContext context, CancellationToken cancellationToken);

    Task<Result<BudgetEnforcementResult>> EnforceBudgetAsync(
        ChatStreamContext context,
        ConversationId conversationId,
        Func<Task<Result<ChatStreamContext>>> rebuildContextAsync,
        CancellationToken cancellationToken
    );
}
```

`Percentage` and `Period` are non-required (default 0 / `BudgetPeriod.Daily`) so the `Allowed` case can keep returning a minimal result.

- [ ] **Step 2: Build to confirm `BudgetGuardService` still compiles against the contract**

Run: `dotnet build Backend/Application/adessoGPT.Application`
Expected: `Build succeeded.` (or pre-existing warnings only; no new errors).

- [ ] **Step 3: Commit**

```bash
git add Backend/Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs
git commit -m "feat: extend BudgetCheckResult with percentage and period fields"
```

---

## Task 3: Refactor `BudgetGuardService` to evaluate highest percentage

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`

- [ ] **Step 1: Replace `IsAnyPeriodExceededAsync` with `EvaluatePeriodsAsync`**

Inside `BudgetGuardService`, replace the `IsAnyPeriodExceededAsync` method with the following new method (keep the rest of the file untouched for now):

```csharp
private async Task<(int MaxPercentage, BudgetPeriod Period)> EvaluatePeriodsAsync(
    BudgetTier tier,
    CancellationToken cancellationToken
)
{
    var checks = new List<(BudgetPeriod Period, long Limit)>(capacity: 3);

    if (tier.DailyTokenLimit is { } daily and > 0)
    {
        checks.Add((BudgetPeriod.Daily, daily));
    }

    if (tier.WeeklyTokenLimit is { } weekly and > 0)
    {
        checks.Add((BudgetPeriod.Weekly, weekly));
    }

    if (tier.MonthlyTokenLimit is { } monthly and > 0)
    {
        checks.Add((BudgetPeriod.Monthly, monthly));
    }

    if (checks.Count == 0)
    {
        return (0, BudgetPeriod.Daily);
    }

    var now = _timeProvider.GetUtcNow();
    var maxPercentage = 0;
    var maxPeriod = BudgetPeriod.Daily;

    foreach (var (period, limit) in checks)
    {
        var stateId = UserBudgetStateId.ForPeriod(period);

        var state = await _dbContext
            .BudgetStates.AsNoTracking()
            .FirstOrDefaultAsync(b => b.Id == stateId, cancellationToken);

        if (state is null)
        {
            continue;
        }

        if (state.PeriodEnd < now)
        {
            continue;
        }

        var percentage = (int)Math.Min(int.MaxValue, state.TokensUsed * 100L / limit);

        if (percentage > maxPercentage)
        {
            maxPercentage = percentage;
            maxPeriod = period;
        }
    }

    return (maxPercentage, maxPeriod);
}
```

- [ ] **Step 2: Rewrite `CheckBudgetAsync` to apply the severity decision**

Replace the existing `CheckBudgetAsync` body with:

```csharp
public async Task<BudgetCheckResult> CheckBudgetAsync(
    ChatStreamContext context,
    CancellationToken cancellationToken
)
{
    var settings = await _singleSettingsRepository.GetSingleSettingsAsync<BudgetLimitSettings>(cancellationToken);

    if (!settings.IsEnabled)
    {
        return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
    }

    var tier = await _budgetTierResolver.ResolveForUserAsync(cancellationToken);

    if (tier is null)
    {
        return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
    }

    var (maxPercentage, maxPeriod) = await EvaluatePeriodsAsync(tier, cancellationToken);

    if (maxPercentage >= 100)
    {
        return await BuildExceededResultAsync(context, maxPercentage, maxPeriod, cancellationToken);
    }

    if (tier.SoftWarningPercent is { } softWarning && maxPercentage >= softWarning)
    {
        return new BudgetCheckResult
        {
            Outcome = BudgetCheckOutcome.Approaching,
            Percentage = maxPercentage,
            Period = maxPeriod,
        };
    }

    return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
}
```

- [ ] **Step 3: Update `BuildExceededResultAsync` signature to carry percentage + period**

Replace the method with:

```csharp
private async Task<BudgetCheckResult> BuildExceededResultAsync(
    ChatStreamContext context,
    int maxPercentage,
    BudgetPeriod maxPeriod,
    CancellationToken cancellationToken
)
{
    var currentModelId = context.ModelExecutionSettings.ModelOptions.Id;

    var agentResult = await _mediator.Send(
        new GetAgentEntityQuery { AgentId = context.Agent.Id },
        cancellationToken
    );

    if (agentResult.IsFailure)
    {
        return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
    }

    var agent = agentResult.Value;
    var fallbackConfig = agent.ModelConfigurations.FirstOrDefault(m => m.IsBudgetFallback);

    if (fallbackConfig is not null && currentModelId == fallbackConfig.ModelOptionsId)
    {
        return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
    }

    if (fallbackConfig is not null)
    {
        var fallbackModelTitle = await GetModelTitleAsync(fallbackConfig.ModelOptionsId, cancellationToken);

        return new BudgetCheckResult
        {
            Outcome = BudgetCheckOutcome.FallbackModel,
            Percentage = maxPercentage,
            Period = maxPeriod,
            OriginalModelOptionsId = currentModelId,
            FallbackModelOptionsId = fallbackConfig.ModelOptionsId,
            FallbackModelTitle = fallbackModelTitle,
        };
    }

    return new BudgetCheckResult
    {
        Outcome = BudgetCheckOutcome.Blocked,
        Percentage = maxPercentage,
        Period = maxPeriod,
    };
}
```

- [ ] **Step 4: Build and verify the service compiles**

Run: `dotnet build Backend/Application/adessoGPT.Application`
Expected: `Build succeeded.` Existing call sites in `EnforceBudgetAsync` will still compile (they don't read `Percentage`/`Period` yet — handled in Task 4).

- [ ] **Step 5: Commit**

```bash
git add Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs
git commit -m "refactor: BudgetGuardService computes highest period percentage"
```

---

## Task 4: Replace event publishing with `ChatBudgetStatusResponse`

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`

- [ ] **Step 1: Update `EnforceBudgetAsync` to handle the new `Approaching` outcome and publish the unified event**

Replace the existing `EnforceBudgetAsync` body with:

```csharp
public async Task<Result<BudgetEnforcementResult>> EnforceBudgetAsync(
    ChatStreamContext context,
    ConversationId conversationId,
    Func<Task<Result<ChatStreamContext>>> rebuildContextAsync,
    CancellationToken cancellationToken
)
{
    var budgetResult = await CheckBudgetAsync(context, cancellationToken);

    if (budgetResult.Outcome == BudgetCheckOutcome.Allowed)
    {
        return new BudgetEnforcementResult { EnforcedContext = context };
    }

    if (budgetResult.Outcome == BudgetCheckOutcome.Approaching)
    {
        context.PublishResponseToChatStream(
            new ChatBudgetStatusResponse
            {
                Severity = BudgetStatusSeverity.Approaching,
                Percentage = budgetResult.Percentage,
                Period = budgetResult.Period,
            }
        );

        return new BudgetEnforcementResult { EnforcedContext = context };
    }

    if (budgetResult.Outcome == BudgetCheckOutcome.Blocked)
    {
        return new BudgetEnforcementResult
        {
            IsBlocked = true,
            BlockedStream = CreateBudgetBlockedStreamAsync(context, budgetResult),
        };
    }

    await _mediator.Send(
        new UpdateConversationModelCommand
        {
            ConversationId = conversationId,
            ModelOptionsId = budgetResult.FallbackModelOptionsId!.Value,
        },
        cancellationToken
    );

    var rebuildResult = await rebuildContextAsync();

    if (rebuildResult.IsFailure)
    {
        return rebuildResult.Error;
    }

    var enforcedContext = rebuildResult.Value;

    enforcedContext.PublishResponseToChatStream(
        new ChatBudgetStatusResponse
        {
            Severity = BudgetStatusSeverity.Warning,
            Percentage = budgetResult.Percentage,
            Period = budgetResult.Period,
            FallbackModelTitle = budgetResult.FallbackModelTitle,
        }
    );

    return new BudgetEnforcementResult { EnforcedContext = enforcedContext };
}
```

- [ ] **Step 2: Update `CreateBudgetBlockedStreamAsync` to publish the new event with `Exhausted` severity**

Replace it with:

```csharp
#pragma warning disable CS1998
private static async IAsyncEnumerable<ChatStreamResponse> CreateBudgetBlockedStreamAsync(
    ChatStreamContext chatStreamContext,
    BudgetCheckResult budgetResult
)
{
    chatStreamContext.PublishResponseToChatStream(
        new ChatBudgetStatusResponse
        {
            Severity = BudgetStatusSeverity.Exhausted,
            Percentage = budgetResult.Percentage,
            Period = budgetResult.Period,
        }
    );

    yield break;
}
#pragma warning restore CS1998
```

- [ ] **Step 3: Remove obsolete `using adessoGPT.Application.Localization;` (no longer needed)**

In `BudgetGuardService.cs`, the `ErrorMessages.Budget_FallbackModel_Warning` / `Budget_Exhausted_Message` references are gone. Drop the now-unused `using adessoGPT.Application.Localization;` from the top of the file.

- [ ] **Step 4: Build the application project**

Run: `dotnet build Backend/Application/adessoGPT.Application`
Expected: `Build succeeded.`

- [ ] **Step 5: Commit**

```bash
git add Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs
git commit -m "feat: publish unified ChatBudgetStatusResponse from BudgetGuardService"
```

---

## Task 5: Delete obsolete event types and unused localization keys

**Files:**
- Delete: `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs`
- Delete: `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs`
- Modify: `Application/adessoGPT.Application/Localization/ErrorMessages.resx` (and `.de.resx`, `.fr.resx`, `.it.resx`, `.Designer.cs`)

- [ ] **Step 1: Delete the old response files**

```bash
rm Backend/Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs
rm Backend/Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs
```

- [ ] **Step 2: Remove the now-unused localization keys**

In each of `ErrorMessages.resx`, `ErrorMessages.de.resx`, `ErrorMessages.fr.resx`, `ErrorMessages.it.resx` under `Backend/Application/adessoGPT.Application/Localization/`, delete the two `<data>` blocks with `name="Budget_Exhausted_Message"` and `name="Budget_FallbackModel_Warning"`.

In `ErrorMessages.Designer.cs` in the same folder, delete the two corresponding generated property blocks (`public static string Budget_Exhausted_Message { ... }` and `public static string Budget_FallbackModel_Warning { ... }`).

- [ ] **Step 3: Verify there are no lingering references**

Run: `grep -rn "ChatBudgetWarningResponse\|ChatBudgetExhaustedResponse\|Budget_Exhausted_Message\|Budget_FallbackModel_Warning" Backend --include="*.cs" --include="*.resx"`
Expected: no matches.

- [ ] **Step 4: Build the full backend solution**

Run: `dotnet build Backend`
Expected: `Build succeeded.`

- [ ] **Step 5: Commit**

```bash
git add -A Backend/Shared/adessoGPT.Chat.Abstractions/Streaming/Updates Backend/Application/adessoGPT.Application/Localization
git commit -m "chore: remove obsolete budget warning/exhausted event types and i18n keys"
```

---

## Task 6: Adapt existing `BudgetGuardServiceTests` to the new contract

**Files:**
- Modify: `Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

The seven existing tests still pass conceptually (settings disabled, tier null, no limits, daily exceeded, weekly exceeded with daily under, state missing, period expired, no fallback → Blocked, already on fallback). They need three small adjustments: assert the new `Percentage` / `Period` fields where relevant and stop relying on `Outcome.Allowed` when the new code returns `Approaching` for the "tokensUsed = 80% with SoftWarningPercent set" boundary (the existing tests don't set `SoftWarningPercent`, so all of them keep returning `Allowed` below 100% — no functional change).

- [ ] **Step 1: Update the `FallbackModel`-asserting test to also check the percentage and period**

In `CheckBudgetAsync_WhenDailyTokensExceeded_ReturnsFallbackModel`, after the existing assertions add:

```csharp
result.Percentage.Should().Be(150);
result.Period.Should().Be(BudgetPeriod.Daily);
```

In `CheckBudgetAsync_WhenWeeklyExceededButDailyUnder_ReturnsFallbackModel`, after the existing assertion add:

```csharp
result.Percentage.Should().Be(100);
result.Period.Should().Be(BudgetPeriod.Weekly);
```

In `CheckBudgetAsync_WhenLimitExceededAndNoFallbackConfigured_ReturnsBlocked`, after the existing assertion add:

```csharp
result.Percentage.Should().Be(200);
result.Period.Should().Be(BudgetPeriod.Monthly);
```

- [ ] **Step 2: Run the existing tests to confirm they still pass**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "FullyQualifiedName~BudgetGuardServiceTests"`
Expected: all existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: assert percentage and period in BudgetGuard outcomes"
```

---

## Task 7: Add tests for the new `Approaching` outcome and percentage selection

**Files:**
- Modify: `Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Extend `TierWith` to optionally set `SoftWarningPercent`**

Replace the existing `TierWith` helper with:

```csharp
private static BudgetTier TierWith(
    long? daily = null,
    long? weekly = null,
    long? monthly = null,
    int? softWarningPercent = null
)
{
    return new BudgetTier
    {
        Id = new BudgetTierId("test-tier"),
        Title = new(),
        Description = new(),
        Priority = 0,
        DailyTokenLimit = daily,
        WeeklyTokenLimit = weekly,
        MonthlyTokenLimit = monthly,
        SoftWarningPercent = softWarningPercent,
    };
}
```

- [ ] **Step 2: Write the failing test for `Approaching` at exactly the soft threshold**

Add to the test class:

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenAtSoftWarningThreshold_ReturnsApproaching()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000, softWarningPercent: 80));
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 800, periodEnd: now.AddHours(14));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Approaching);
    result.Percentage.Should().Be(80);
    result.Period.Should().Be(BudgetPeriod.Daily);
    await _mediator.DidNotReceive().Send(Arg.Any<GetAgentEntityQuery>(), Arg.Any<CancellationToken>());
}
```

- [ ] **Step 3: Run the test, confirm it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenAtSoftWarningThreshold_ReturnsApproaching"`
Expected: PASS.

- [ ] **Step 4: Add a test for `null` soft-warning ⇒ no Approaching even at 90%**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenSoftWarningIsNull_ReturnsAllowedBelowHardLimit()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000, softWarningPercent: null));
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 900, periodEnd: now.AddHours(14));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
}
```

- [ ] **Step 5: Add a test for highest-percentage selection across multiple periods**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenMultiplePeriodsApproaching_ReportsHighestPercentage()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000, weekly: 10_000, softWarningPercent: 80));
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 850, periodEnd: now.AddHours(14));
    await SeedBudgetStateAsync(BudgetPeriod.Weekly, tokensUsed: 9200, periodEnd: now.AddDays(2));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Approaching);
    result.Percentage.Should().Be(92);
    result.Period.Should().Be(BudgetPeriod.Weekly);
}
```

- [ ] **Step 6: Add a test asserting `Allowed` just below the soft threshold**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenJustBelowSoftThreshold_ReturnsAllowed()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000, softWarningPercent: 80));
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 799, periodEnd: now.AddHours(14));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
}
```

- [ ] **Step 7: Run the full test class**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "FullyQualifiedName~BudgetGuardServiceTests"`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: cover Approaching outcome and highest-percentage selection"
```

---

## Task 8: Update `Backend/.claude/rules/budget.md`

**Files:**
- Modify: `Backend/.claude/rules/budget.md`

- [ ] **Step 1: Add a new section after "Tier Resolution" documenting the SSE event**

Append the following section:

```markdown
## Chat-Stream Budget Events

`BudgetGuardService.EnforceBudgetAsync` publishes a single SSE event on the chat stream when the user's budget state crosses a threshold:

| Outcome | Severity | Trigger | Stream behavior |
|---|---|---|---|
| `Approaching` | `Approaching` | `tier.SoftWarningPercent` is set AND highest period pct ≥ that value AND < 100 | Continues normally |
| `FallbackModel` | `Warning` | Highest pct ≥ 100 AND agent has an `IsBudgetFallback` model AND user is not already on it | Switches conversation to fallback model, includes `FallbackModelTitle`, continues |
| `Blocked` | `Exhausted` | Highest pct ≥ 100 AND no fallback configured | Stream ends (`yield break`) |

The event type is `ChatBudgetStatusResponse` (`event: "budget_status"`). It carries `Severity`, the highest `Percentage` across all periods with a configured limit, the corresponding `Period` (Daily/Weekly/Monthly), and `FallbackModelTitle` (only for `Warning`).

`BudgetTier.SoftWarningPercent = null` means **no Approaching event** for that tier — the field is an explicit opt-in to soft warnings, consistent with the nullable token-limit semantics.

The service is stateless: the event fires on every chat send above the threshold. Throttling/dismiss is a frontend concern.
```

- [ ] **Step 2: Commit**

```bash
git add Backend/.claude/rules/budget.md
git commit -m "docs: document budget_status SSE event in backend rules"
```

---

## Task 9: Format, run all backend tests, and validate startup

**Files:** none (project-wide)

- [ ] **Step 1: Format**

Run: `cd Backend && dotnet csharpier format .`
Expected: no errors.

- [ ] **Step 2: Run the full test suite**

Run: `dotnet test Backend`
Expected: all tests pass.

- [ ] **Step 3: Run the IntegrationTest profile to validate startup (form/seed validators)**

Run (in a separate terminal): `cd Backend/Presentation/adessoGPT.Presentation.Api && dotnet run --launch-profile IntegrationTest`
Watch for: `Now listening on: http://localhost:5522`. Then kill the process.
Expected: clean startup, no `InvalidOperationException` from `FormsServiceStartupValidator` or `SynchronizeDatabaseWithConfigurationAsync`.

- [ ] **Step 4: Commit any formatter changes**

```bash
git add -A Backend
git diff --cached --quiet || git commit -m "chore: csharpier format"
```

---

## Task 10: Regenerate the OpenAPI spec for the frontend handover

**Files:** none here — produces output for the Angular client regeneration that the frontend agent will run.

- [ ] **Step 1: Start the backend in IntegrationTest mode**

Run (background): `cd Backend/Presentation/adessoGPT.Presentation.Api && dotnet run --launch-profile IntegrationTest`
Wait for: `Now listening on: http://localhost:5522`.

- [ ] **Step 2: Hand off**

The backend is now ready for the frontend agent to regenerate the API client (`Frontend/adessoGPT.Web && npm run generate:api`). Frontend changes follow the spec at `configs/budget-limiting/Backend/docs/2026-04-28-budget-banner-frontend-handover.md`.

Kill the backend process once the frontend agent has finished its regeneration.

---

## Self-Review

1. **Spec coverage:**
   - Single `budget_status` event with severity discriminator → Task 1.
   - `Approaching` outcome on `BudgetCheckOutcome`, `Percentage`/`Period` on `BudgetCheckResult` → Task 2.
   - Highest percentage across periods (skip null/zero limits) → Task 3.
   - Severity decision tree (Warning > Exhausted > Approaching > Allowed) → Task 3 + Task 4.
   - Publish unified event for Approaching/Warning/Exhausted; Blocked still `yield break`s → Task 4.
   - Delete old event types + unused i18n keys → Task 5.
   - Tests for Approaching, null soft-warning, highest-pct, just-below-threshold → Task 7.
   - Existing tests adapted to new result shape → Task 6.
   - Rules update → Task 8.
   - Format + integration startup validation → Task 9.

2. **Placeholder scan:** No "TBD"/"TODO"/vague entries; every code step contains the exact code.

3. **Type consistency:** `BudgetStatusSeverity` (Approaching/Warning/Exhausted), `BudgetCheckOutcome` (Allowed/Approaching/FallbackModel/Blocked), `BudgetPeriod` (Daily/Weekly/Monthly), `BudgetCheckResult.Percentage` (int), `BudgetCheckResult.Period` (BudgetPeriod) used consistently across all tasks. `EvaluatePeriodsAsync` returns `(int MaxPercentage, BudgetPeriod Period)` — referenced unchanged in `CheckBudgetAsync`.
