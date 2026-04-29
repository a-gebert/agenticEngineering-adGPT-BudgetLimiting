# Budget Guard — Tier-Based Limit Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hard-coded global `MonthlyTokenLimit` check in `BudgetGuardService.CheckBudgetAsync` with per-user, tier-driven daily/weekly/monthly token-limit enforcement that delegates tier resolution to `IBudgetTierResolver`.

**Architecture:** `BudgetGuardService` gains two new dependencies — `IBudgetTierResolver` (already FusionCache-backed) and `TimeProvider` (for the expired-period check). The new `CheckBudgetAsync` flow is: settings on/off → resolve tier → for every non-null period limit on the tier, load `UserBudgetState` and decide. Missing state and expired `PeriodEnd` are both treated as 0 usage. If any single period exceeds its limit, the existing fallback-model / blocked decision tree runs unchanged.

**Tech Stack:** .NET 10, EF Core 10 (in-memory provider for tests), MediatR, NSubstitute, xUnit, FluentAssertions, `FakeTimeProvider` from `Microsoft.Extensions.TimeProvider.Testing`.

**Spec:** `configs/budget-limiting/Backend/docs/superpowers/specs/2026-04-27-budget-guard-tier-integration-design.md`

---

## File Structure

### Modified Files

| File | Change |
|------|--------|
| `Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs` | Inject `IBudgetTierResolver` + `TimeProvider`; rewrite `CheckBudgetAsync` to drive period checks from the resolved tier. `EnforceBudgetAsync`, `CreateBudgetBlockedStreamAsync`, `GetModelTitleAsync` stay byte-identical. |

### New Files

| File | Responsibility |
|------|---------------|
| `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs` | Unit tests for `BudgetGuardService.CheckBudgetAsync` covering every branch in the new flow. |

### Unchanged

| File | Note |
|------|------|
| `Backend/Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs` | Public contract is stable — no new fields on `BudgetCheckResult`, no new outcomes. |
| `Backend/Application/adessoGPT.Application/ApplicationModule.cs` | `IBudgetTierResolver` is already registered as `Scoped`. `TimeProvider.System` is already available globally — no DI change needed. |
| All five chat-stream call sites of `EnforceBudgetAsync` | Behavior-preserving change; they keep calling the same method. |

---

## Background — what each existing piece already gives us

These are facts about the current code that the implementer must NOT re-derive — drift here causes silent bugs:

- `UserBudgetStateId.ForPeriod(BudgetPeriod period)` exists at `Backend/Shared/adessoGPT.Domain/PersistedEntities/Budget/UserBudgetState.cs:16`. Returns the deterministic ID `budget-monthly` / `budget-weekly` / `budget-daily`. Use it directly — do NOT compose strings.
- `IUserDbContext.BudgetStates` is partitioned per user (`UserPartitionedEntity`). Filtering by `Id` alone is sufficient — the EF query filter scopes to the current user.
- `IBudgetTierResolver.ResolveForUserAsync(CancellationToken)` returns `BudgetTier?`. `null` means "no tier matched and no default tier exists" → unlimited. The resolver hits FusionCache, so calling it on every chat turn is cheap.
- `BudgetTier.DailyTokenLimit`, `WeeklyTokenLimit`, `MonthlyTokenLimit` are all `long?`. A null value means "this period is not enforced for this tier".
- `BudgetLimitSettings.IsEnabled` stays the master kill-switch. `BudgetLimitSettings.MonthlyTokenLimit` is no longer consulted by per-user enforcement and must be left untouched (it is still used elsewhere as a company-wide reference metric).
- `ApplicationCqrsTestBase` builds a full DI container with an in-memory `IUserDbContext`. The `DataSeeder` accepts entities; `FakeTimeProvider` is registered as the singleton `TimeProvider`. Service tests in this codebase usually instantiate the SUT directly with a mix of real DI services (DbContext, FakeTimeProvider) and NSubstitute mocks (the rest) — see `ThumbnailGeneratorServiceTests` for the bare-NSubstitute style.

---

### Task 1: Inject the new dependencies into `BudgetGuardService` (no behavior change)

This is a pure refactor that keeps the existing global-limit logic intact. Goal: confirm the DI graph still resolves and every existing call site (5 chat handlers) still compiles. No new behavior yet — that comes in Task 3+.

**Files:**
- Modify: `Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`

- [ ] **Step 1: Add the two new fields and constructor parameters**

Open `BudgetGuardService.cs` and replace the field block + constructor with:

```csharp
private readonly IUserDbContext _dbContext;
private readonly IMediator _mediator;
private readonly IModelOptionsRepository _modelOptionsRepository;
private readonly ISingleSettingsRepository _singleSettingsRepository;
private readonly IBudgetTierResolver _budgetTierResolver;
private readonly TimeProvider _timeProvider;

public BudgetGuardService(
    IUserDbContext dbContext,
    IMediator mediator,
    IModelOptionsRepository modelOptionsRepository,
    ISingleSettingsRepository singleSettingsRepository,
    IBudgetTierResolver budgetTierResolver,
    TimeProvider timeProvider
)
{
    _dbContext = dbContext;
    _mediator = mediator;
    _modelOptionsRepository = modelOptionsRepository;
    _singleSettingsRepository = singleSettingsRepository;
    _budgetTierResolver = budgetTierResolver;
    _timeProvider = timeProvider;
}
```

- [ ] **Step 2: Verify the build**

Run: `dotnet build` (from `Backend/`)
Expected: Build succeeds. No call sites need to change — they all go through `IBudgetGuardService`. DI registration in `ApplicationModule.cs` already covers `IBudgetTierResolver`; `TimeProvider.System` is registered globally by `Microsoft.Extensions.Hosting`.

- [ ] **Step 3: Commit**

```bash
git add Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs
git commit -m "refactor: inject IBudgetTierResolver and TimeProvider into BudgetGuardService"
```

---

### Task 2: Create the test class scaffolding

Set up the test fixture once so subsequent tasks just add `[Fact]` methods. This task creates the file with the `Setup` helper but only a single trivial assertion to confirm the harness wires up correctly.

**Files:**
- Create: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Create the test file with fixture, helpers, and one passing sanity test**

```csharp
namespace adessoGPT.Application.Tests.Business.Budget;

using System.Collections.Immutable;
using adessoGPT.Application.Business.Agents.GetAgentEntity;
using adessoGPT.Application.Business.Budget.Services;
using adessoGPT.Application.Business.ModelOptions;
using adessoGPT.Application.Business.Settings;
using adessoGPT.Chat.Abstractions.Streaming;
using adessoGPT.Core.Results;
using adessoGPT.Core.Users;
using adessoGPT.Domain;
using adessoGPT.Domain.PersistedEntities.Agents;
using adessoGPT.Domain.PersistedEntities.Budget;
using adessoGPT.Domain.PersistedEntities.System.Settings.BudgetTier;
using adessoGPT.Domain.PersistedEntities.System.Settings.ModelOptions;
using adessoGPT.Domain.PersistedEntities.System.SingleSettings;
using adessoGPT.Domain.PersistedEntities.User.Conversation;
using FluentAssertions;
using MediatR;
using Microsoft.Extensions.Logging;
using NSubstitute;
using Xunit;
using Xunit.Abstractions;

public class BudgetGuardServiceTests : ApplicationCqrsTestBase
{
    private readonly IBudgetTierResolver _tierResolver = Substitute.For<IBudgetTierResolver>();
    private readonly ISingleSettingsRepository _settingsRepository = Substitute.For<ISingleSettingsRepository>();
    private readonly IModelOptionsRepository _modelOptionsRepository = Substitute.For<IModelOptionsRepository>();
    private readonly IMediator _mediator = Substitute.For<IMediator>();

    private static readonly AgentId TestAgentId = new("test-agent");
    private static readonly ModelOptionsId DefaultModelId = new("model-default");
    private static readonly ModelOptionsId FallbackModelId = new("model-fallback");

    public BudgetGuardServiceTests(ITestOutputHelper testOutputHelper)
        : base(testOutputHelper) { }

    private BudgetGuardService CreateSut()
    {
        return new BudgetGuardService(
            DbContext,
            _mediator,
            _modelOptionsRepository,
            _settingsRepository,
            _tierResolver,
            FakeTimeProvider
        );
    }

    private void GivenSettings(bool isEnabled)
    {
        _settingsRepository
            .GetSingleSettingsAsync<BudgetLimitSettings>(Arg.Any<CancellationToken>())
            .Returns(new BudgetLimitSettings { IsEnabled = isEnabled, MonthlyTokenLimit = null });
    }

    private void GivenTier(BudgetTier? tier)
    {
        _tierResolver.ResolveForUserAsync(Arg.Any<CancellationToken>()).Returns(tier);
    }

    private static BudgetTier TierWith(
        long? daily = null,
        long? weekly = null,
        long? monthly = null
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
        };
    }

    private async Task SeedBudgetStateAsync(
        BudgetPeriod period,
        long tokensUsed,
        DateTimeOffset periodEnd
    )
    {
        var state = UserBudgetState.Create(
            UserBudgetState.CalculatePeriodStart(periodEnd.AddSeconds(-1), period),
            period
        );
        state.TokensUsed = tokensUsed;
        state.PeriodEnd = periodEnd;
        DbContext.BudgetStates.Add(state);
        await DbContext.SaveChangesAsync(CancellationToken.None);
    }

    private static ChatStreamContext CreateContext(ModelOptionsId currentModelId)
    {
        var agent = Substitute.For<ChatStreamAgent>();
        agent.Id.Returns(TestAgentId);

        var modelOptions = Substitute.For<ChatModelOptionsBase>();
        modelOptions.Id.Returns(currentModelId);

        var settings = Substitute.For<ChatStreamModelExecutionSettings>();
        settings.ModelOptions.Returns(modelOptions);

        var context = Substitute.For<ChatStreamContext>(
            false,
            Substitute.For<adessoGPT.Chat.Abstractions.Citations.ICitationProcessor>()
        );
        context.Agent.Returns(agent);
        context.ModelExecutionSettings.Returns(settings);

        return context;
    }

    [Fact]
    public async Task CheckBudgetAsync_WhenSettingsDisabled_ReturnsAllowed()
    {
        // Arrange
        GivenSettings(isEnabled: false);
        var sut = CreateSut();

        // Act
        var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

        // Assert
        result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
        await _tierResolver.DidNotReceive().ResolveForUserAsync(Arg.Any<CancellationToken>());
    }
}
```

> **Note on `CreateContext`**: `ChatStreamContext` is normally instantiated via the `new ChatStreamContext(...)` { ... } init-pattern as in `Backend/Tests/Application/adessoGPT.Application.MCP.Tests/ExternalOAuthConnectionWaiterTests.cs:140`. If `Substitute.For<ChatStreamContext>(...)` cannot be used (sealed/non-virtual properties), fall back to that init-pattern verbatim — the test only needs `.Agent.Id` and `.ModelExecutionSettings.ModelOptions.Id` to be reachable.

- [ ] **Step 2: Run the test to verify wiring**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "FullyQualifiedName~BudgetGuardServiceTests"`
Expected: 1 test passes (`CheckBudgetAsync_WhenSettingsDisabled_ReturnsAllowed`).

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: scaffold BudgetGuardServiceTests with disabled-settings sanity case"
```

---

### Task 3: No tier resolved → return Allowed

**Files:**
- Modify: `Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Write the failing test**

Append to `BudgetGuardServiceTests.cs`:

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenNoTierResolves_ReturnsAllowed()
{
    // Arrange
    GivenSettings(isEnabled: true);
    GivenTier(null);
    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenNoTierResolves_ReturnsAllowed"`
Expected: FAIL — current implementation queries `_dbContext.BudgetStates` for `budget-monthly` (returns null because nothing seeded), reads the global `BudgetLimitSettings.MonthlyTokenLimit` (null in the test → `long.MaxValue`), and falls through. Whether it currently passes or fails depends on the early-return — the goal of this task is to make the assertion robust against the new implementation. If it already passes here, that's fine; the next task makes the failure unambiguous.

- [ ] **Step 3: Replace `CheckBudgetAsync` with the tier-driven flow (minimal version)**

In `BudgetGuardService.cs`, replace the entire `CheckBudgetAsync` method with the following. This deletes the global-limit lookup and substitutes the tier resolver. Period checks come in Task 4+.

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

    var anyPeriodExceeded = await IsAnyPeriodExceededAsync(tier, cancellationToken);

    if (!anyPeriodExceeded)
    {
        return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
    }

    return await BuildExceededResultAsync(context, cancellationToken);
}

private Task<bool> IsAnyPeriodExceededAsync(BudgetTier tier, CancellationToken cancellationToken)
{
    // Filled in by Task 4. For now, no tier limits are checked.
    return Task.FromResult(false);
}

private async Task<BudgetCheckResult> BuildExceededResultAsync(
    ChatStreamContext context,
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
            OriginalModelOptionsId = currentModelId,
            FallbackModelOptionsId = fallbackConfig.ModelOptionsId,
            FallbackModelTitle = fallbackModelTitle,
        };
    }

    return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Blocked };
}
```

The two helper methods preserve the original fallback/block decision tree verbatim — nothing about that part of the contract changes.

- [ ] **Step 4: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenNoTierResolves_ReturnsAllowed"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "feat: route BudgetGuardService through IBudgetTierResolver"
```

---

### Task 4: Tier with no limits → Allowed (zero-period case)

**Files:**
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

This case verifies the helper short-circuits when every limit on the tier is null (e.g. an unrestricted "Power" tier).

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenTierHasNoLimits_ReturnsAllowed()
{
    // Arrange
    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: null, weekly: null, monthly: null));
    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
    await _mediator.DidNotReceive().Send(Arg.Any<GetAgentEntityQuery>(), Arg.Any<CancellationToken>());
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenTierHasNoLimits_ReturnsAllowed"`
Expected: PASS — `IsAnyPeriodExceededAsync` is currently a stub that returns `false`, which is correct for this case. This test locks the behavior in before Task 5 expands the helper.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: BudgetGuard returns Allowed when tier configures no limits"
```

---

### Task 5: Daily limit exceeded → triggers fallback model

This is the first test that exercises the period-check loop and forces the real implementation of `IsAnyPeriodExceededAsync`.

**Files:**
- Modify: `Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenDailyTokensExceeded_ReturnsFallbackModel()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000));
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 1500, periodEnd: now.AddHours(14));

    var agent = new Agent
    {
        Id = TestAgentId,
        Title = new(),
        Description = new(),
        SystemMessage = string.Empty,
        ModelConfigurations =
        [
            new AgentModelConfiguration
            {
                ModelOptionsId = FallbackModelId,
                IsBudgetFallback = true,
                IsDefault = false,
            },
        ],
    };
    _mediator
        .Send(Arg.Is<GetAgentEntityQuery>(q => q.AgentId == TestAgentId), Arg.Any<CancellationToken>())
        .Returns(Result<Agent>.Success(agent));
    _modelOptionsRepository
        .GetByIdAsync(FallbackModelId, Arg.Any<CancellationToken>())
        .Returns((ChatModelOptionsBase?)null);

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.FallbackModel);
    result.OriginalModelOptionsId.Should().Be(DefaultModelId);
    result.FallbackModelOptionsId.Should().Be(FallbackModelId);
}
```

> If the `Agent` builder above doesn't compile because of additional required fields, use `AgentBuilder` (`adessoGPT.Tests.Core.DataSeeding`) — `.WithId(TestAgentId)` plus a manual `ModelConfigurations` list. Either way, the test only needs an Agent whose first `IsBudgetFallback` config points at `FallbackModelId`.

- [ ] **Step 2: Run test to verify it fails**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenDailyTokensExceeded_ReturnsFallbackModel"`
Expected: FAIL — `result.Outcome` is `Allowed`. The stub `IsAnyPeriodExceededAsync` always returns `false`.

- [ ] **Step 3: Implement the period-check helper**

Replace the stub in `BudgetGuardService.cs` with the real implementation:

```csharp
private async Task<bool> IsAnyPeriodExceededAsync(BudgetTier tier, CancellationToken cancellationToken)
{
    var checks = new List<(BudgetPeriod Period, long Limit)>(capacity: 3);

    if (tier.DailyTokenLimit.HasValue)
    {
        checks.Add((BudgetPeriod.Daily, tier.DailyTokenLimit.Value));
    }

    if (tier.WeeklyTokenLimit.HasValue)
    {
        checks.Add((BudgetPeriod.Weekly, tier.WeeklyTokenLimit.Value));
    }

    if (tier.MonthlyTokenLimit.HasValue)
    {
        checks.Add((BudgetPeriod.Monthly, tier.MonthlyTokenLimit.Value));
    }

    if (checks.Count == 0)
    {
        return false;
    }

    var now = _timeProvider.GetUtcNow();

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

        if (state.TokensUsed >= limit)
        {
            return true;
        }
    }

    return false;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenDailyTokensExceeded_ReturnsFallbackModel"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "feat: enforce per-period token limits from resolved BudgetTier"
```

---

### Task 6: Weekly limit exceeded but daily under → fallback (proves loop iterates beyond first period)

**Files:**
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenWeeklyExceededButDailyUnder_ReturnsFallbackModel()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000, weekly: 5000));
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 200, periodEnd: now.AddHours(14));
    await SeedBudgetStateAsync(BudgetPeriod.Weekly, tokensUsed: 5000, periodEnd: now.AddDays(2));

    var agent = new Agent
    {
        Id = TestAgentId,
        Title = new(),
        Description = new(),
        SystemMessage = string.Empty,
        ModelConfigurations =
        [
            new AgentModelConfiguration
            {
                ModelOptionsId = FallbackModelId,
                IsBudgetFallback = true,
                IsDefault = false,
            },
        ],
    };
    _mediator
        .Send(Arg.Is<GetAgentEntityQuery>(q => q.AgentId == TestAgentId), Arg.Any<CancellationToken>())
        .Returns(Result<Agent>.Success(agent));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.FallbackModel);
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenWeeklyExceededButDailyUnder_ReturnsFallbackModel"`
Expected: PASS — the implementation already iterates all configured periods.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: BudgetGuard checks weekly when daily is under limit"
```

---

### Task 7: Missing state document → treated as 0 usage

**Files:**
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenStateMissingForConfiguredPeriod_ReturnsAllowed()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000, monthly: 100_000));
    // No UserBudgetState seeded — fresh user, no usage yet.

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
    await _mediator.DidNotReceive().Send(Arg.Any<GetAgentEntityQuery>(), Arg.Any<CancellationToken>());
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenStateMissingForConfiguredPeriod_ReturnsAllowed"`
Expected: PASS — the `state is null → continue` branch already handles this.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: BudgetGuard treats missing UserBudgetState as zero usage"
```

---

### Task 8: Expired `PeriodEnd` → treated as 0 usage

**Files:**
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

This test verifies the rollover semantics — yesterday's exhausted daily state must NOT block today's chat.

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenPeriodEndIsExpired_TreatsStateAsZero()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(daily: 1000));
    // Stale state from yesterday: TokensUsed exceeds the limit, but PeriodEnd has passed.
    await SeedBudgetStateAsync(BudgetPeriod.Daily, tokensUsed: 9999, periodEnd: now.AddHours(-1));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenPeriodEndIsExpired_TreatsStateAsZero"`
Expected: PASS — the `state.PeriodEnd < now → continue` branch already handles this.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: BudgetGuard treats expired UserBudgetState as zero usage"
```

---

### Task 9: No fallback model configured → return Blocked

**Files:**
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenLimitExceededAndNoFallbackConfigured_ReturnsBlocked()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(monthly: 1000));
    await SeedBudgetStateAsync(BudgetPeriod.Monthly, tokensUsed: 2000, periodEnd: now.AddDays(3));

    var agent = new Agent
    {
        Id = TestAgentId,
        Title = new(),
        Description = new(),
        SystemMessage = string.Empty,
        ModelConfigurations =
        [
            new AgentModelConfiguration
            {
                ModelOptionsId = DefaultModelId,
                IsBudgetFallback = false,
                IsDefault = true,
            },
        ],
    };
    _mediator
        .Send(Arg.Is<GetAgentEntityQuery>(q => q.AgentId == TestAgentId), Arg.Any<CancellationToken>())
        .Returns(Result<Agent>.Success(agent));

    var sut = CreateSut();

    // Act
    var result = await sut.CheckBudgetAsync(CreateContext(DefaultModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Blocked);
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenLimitExceededAndNoFallbackConfigured_ReturnsBlocked"`
Expected: PASS — the unchanged `BuildExceededResultAsync` returns `Blocked` when no `IsBudgetFallback` config exists.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: BudgetGuard returns Blocked when no fallback model is configured"
```

---

### Task 10: Already on the fallback model → return Allowed (re-entry guard)

This protects the chat from looping into a fallback that is itself over budget — once the user is on the fallback, they stay on it for the rest of the period.

**Files:**
- Modify: `Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs`

- [ ] **Step 1: Write the failing test**

```csharp
[Fact]
public async Task CheckBudgetAsync_WhenAlreadyOnFallbackModel_ReturnsAllowed()
{
    // Arrange
    var now = new DateTimeOffset(2026, 4, 27, 10, 0, 0, TimeSpan.Zero);
    FakeTimeProvider.SetUtcNow(now);

    GivenSettings(isEnabled: true);
    GivenTier(TierWith(monthly: 1000));
    await SeedBudgetStateAsync(BudgetPeriod.Monthly, tokensUsed: 2000, periodEnd: now.AddDays(3));

    var agent = new Agent
    {
        Id = TestAgentId,
        Title = new(),
        Description = new(),
        SystemMessage = string.Empty,
        ModelConfigurations =
        [
            new AgentModelConfiguration
            {
                ModelOptionsId = FallbackModelId,
                IsBudgetFallback = true,
                IsDefault = false,
            },
        ],
    };
    _mediator
        .Send(Arg.Is<GetAgentEntityQuery>(q => q.AgentId == TestAgentId), Arg.Any<CancellationToken>())
        .Returns(Result<Agent>.Success(agent));

    var sut = CreateSut();

    // Act — current model IS the fallback model.
    var result = await sut.CheckBudgetAsync(CreateContext(FallbackModelId), CancellationToken.None);

    // Assert
    result.Outcome.Should().Be(BudgetCheckOutcome.Allowed);
}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `dotnet test Backend/Tests/Application/adessoGPT.Application.Tests --filter "Name=CheckBudgetAsync_WhenAlreadyOnFallbackModel_ReturnsAllowed"`
Expected: PASS — `BuildExceededResultAsync` short-circuits when `currentModelId == fallbackConfig.ModelOptionsId`.

- [ ] **Step 3: Commit**

```bash
git add Backend/Tests/Application/adessoGPT.Application.Tests/Business/Budget/BudgetGuardServiceTests.cs
git commit -m "test: BudgetGuard returns Allowed when already on fallback model"
```

---

### Task 11: Final formatting, full-suite run, and IntegrationTest profile smoke check

**Files:**
- All modified files (no further code edits expected).

- [ ] **Step 1: Format**

Run: `cd Backend && dotnet csharpier format .`
Expected: Either no changes, or whitespace-only changes. If anything functional changes, investigate.

- [ ] **Step 2: Run the full backend test suite**

Run: `cd Backend && dotnet test`
Expected: All tests pass. Pay specific attention to anything that exercises `IBudgetGuardService` indirectly — `StartChatConversationCommand`, `ResumeChatConversationCommand`, `RegenerateAssistantChatMessageCommand`, `ChangeUserChatMessageCommand`, `StartRealtimeChatConversationCommand`. They all keep working because the public interface didn't change and DI now resolves the two new dependencies (`IBudgetTierResolver` is already registered; `TimeProvider` is registered by the host).

- [ ] **Step 3: Smoke-test the IntegrationTest launch profile**

Run:

```bash
cd Backend/Presentation/adessoGPT.Presentation.Api
dotnet run --launch-profile IntegrationTest
```

Wait for `Now listening on: http://localhost:5522` then kill the process (`Ctrl+C`).
Expected: Clean startup. The schema-evolution rule (`persistence.md`) demands this whenever an injected service set changes — we want to confirm DI resolution and the synchronisation pass succeed.

- [ ] **Step 4: Commit any formatter changes**

```bash
git add -u
git diff --cached --quiet || git commit -m "chore: csharpier format"
```

- [ ] **Step 5: Update rules — capture the new BudgetGuardService dependency on IBudgetTierResolver**

The CLAUDE.md "Continuous Learning (MANDATORY)" rule requires recording new patterns. Add a short bullet to the existing `Backend/.claude/rules/budget-tier.md` (created by the prior plan) noting that `BudgetGuardService` now consumes `IBudgetTierResolver` for per-user limit enforcement, and that `BudgetLimitSettings.MonthlyTokenLimit` is no longer used as a per-user limit. If the file does not yet describe `BudgetGuardService`, add a new section "Enforcement"; if it does, edit the existing section.

```bash
git add Backend/.claude/rules/budget-tier.md
git diff --cached --quiet || git commit -m "docs: budget-tier rule covers BudgetGuard enforcement integration"
```

---

## Self-Review

**1. Spec coverage** — every numbered step in the spec's "Modified CheckBudgetAsync Flow" maps to a task:

| Spec step | Tasks |
|---|---|
| `!IsEnabled → Allowed` | Task 2 (sanity test, behavior unchanged) |
| `tier == null → Allowed` | Task 3 |
| Build period checks from non-null limits | Task 5 (helper implementation) |
| `state is null → 0 usage → OK` | Task 7 |
| `state.PeriodEnd < UtcNow → 0 usage → OK` | Task 8 |
| `state.TokensUsed >= limit → EXCEEDED` | Tasks 5, 6 |
| Any period exceeded → fallback/block logic | Tasks 5, 9, 10 |
| No period exceeded → Allowed | Task 4, Task 7 |
| Caching strategy (resolver-only) | Task 1 — no extra cache layer added |
| State creation is lazy | Implicit — `CheckBudgetAsync` only reads, never writes |
| `MonthlyTokenLimit` no longer per-user | Task 3 — global limit lookup is deleted in the new `CheckBudgetAsync` |

**2. Placeholder scan** — every code block contains real, runnable code. No `TODO`, no "implement later", no "similar to Task N". The one cross-task reference (Task 4 → Task 5 implements the helper) is explicit about what's stubbed and why.

**3. Type consistency** — `IsAnyPeriodExceededAsync` is used by Task 3's stub and Task 5's real implementation; the signature is identical (`Task<bool>`, takes `BudgetTier` + `CancellationToken`). `BuildExceededResultAsync` keeps the same `Task<BudgetCheckResult>` signature throughout. `TestAgentId`, `DefaultModelId`, `FallbackModelId`, `TierWith`, `SeedBudgetStateAsync`, `CreateContext` are all defined once in Task 2 and reused unchanged across Tasks 3–10. `_tierResolver`, `_settingsRepository`, `_modelOptionsRepository`, `_mediator` keep the same types and field names everywhere they appear.

**4. Outside-the-spec risk check** — the plan deliberately leaves these unchanged: `EnforceBudgetAsync`, `BudgetCheckResult`, `BudgetCheckOutcome`, the five chat handler call sites, `BudgetLimitSettings.MonthlyTokenLimit` (still used elsewhere as a company-wide reference). No frontend changes, no API client regeneration — the public contract is stable.
