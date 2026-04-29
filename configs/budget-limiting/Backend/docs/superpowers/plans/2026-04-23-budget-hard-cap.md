# Budget Hard Cap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce a monthly token hard cap before the LLM call, with fallback to a free model when budget is exceeded.

**Architecture:** `IBudgetGuardService` is called from all chat handlers between context creation and stream creation. It reads the monthly `UserBudgetState`, compares against a hardcoded cap, and returns Allowed / FallbackModel / Blocked. On FallbackModel, the handler updates the conversation model and rebuilds the context. On Blocked, a `ChatBudgetExhaustedResponse` is returned instead of a stream.

**Tech Stack:** .NET 10, MediatR, FluentValidation, xUnit + NSubstitute

**Spec:** `configs/budget-limiting/Backend/docs/superpowers/specs/2026-04-23-budget-hard-cap-design.md`

---

### Task 1: Add `IsBudgetFallback` to AgentModelConfiguration

**Files:**
- Modify: `Shared/adessoGPT.Domain/PersistedEntities/System/Settings/Agent/AgentModelConfiguration.cs`

- [ ] **Step 1: Add the property**

In `Shared/adessoGPT.Domain/PersistedEntities/System/Settings/Agent/AgentModelConfiguration.cs`, add after the `Order` property (line 46):

```csharp
/// <summary>
/// Whether this model is used as a free fallback when the user's budget is exhausted.
/// At most one model per agent should have this set to true.
/// </summary>
public bool IsBudgetFallback { get; init; }
```

- [ ] **Step 2: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`
Expected: Build succeeded, 0 errors.

- [ ] **Step 3: Commit**

```bash
git add Shared/adessoGPT.Domain/PersistedEntities/System/Settings/Agent/AgentModelConfiguration.cs
git commit -m "feat(budget): add IsBudgetFallback to AgentModelConfiguration"
```

---

### Task 2: Create ChatStream budget response types

**Files:**
- Create: `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs`
- Create: `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs`

- [ ] **Step 1: Create ChatBudgetWarningResponse**

Create `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs`:

```csharp
namespace adessoGPT.Chat.Abstractions.Streaming.Updates;

public record ChatBudgetWarningResponse : ChatStreamResponse
{
    public ChatBudgetWarningResponse()
        : base("budget_warning") { }

    public required string Message { get; init; }
    public required string FallbackModelTitle { get; init; }
}
```

- [ ] **Step 2: Create ChatBudgetExhaustedResponse**

Create `Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs`:

```csharp
namespace adessoGPT.Chat.Abstractions.Streaming.Updates;

public record ChatBudgetExhaustedResponse : ChatStreamResponse
{
    public ChatBudgetExhaustedResponse()
        : base("budget_exhausted") { }

    public required string Message { get; init; }
}
```

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`
Expected: Build succeeded, 0 errors.

- [ ] **Step 4: Commit**

```bash
git add Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetWarningResponse.cs
git add Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/ChatBudgetExhaustedResponse.cs
git commit -m "feat(budget): add ChatBudgetWarningResponse and ChatBudgetExhaustedResponse"
```

---

### Task 3: Add localization keys for budget messages

**Files:**
- Modify: `Application/adessoGPT.Application/Localization/ErrorMessages.resx`
- Modify: `Application/adessoGPT.Application/Localization/ErrorMessages.de.resx`
- Modify: `Application/adessoGPT.Application/Localization/ErrorMessages.fr.resx`
- Modify: `Application/adessoGPT.Application/Localization/ErrorMessages.it.resx`

- [ ] **Step 1: Add English keys**

In `Application/adessoGPT.Application/Localization/ErrorMessages.resx`, add before the closing `</root>` tag:

```xml
  <data name="Budget_Exhausted_Message" xml:space="preserve">
    <value>Your monthly budget has been exhausted.</value>
  </data>
  <data name="Budget_FallbackModel_Warning" xml:space="preserve">
    <value>Budget exceeded. Switched to {0}.</value>
  </data>
```

- [ ] **Step 2: Add German keys**

In `Application/adessoGPT.Application/Localization/ErrorMessages.de.resx`, add before the closing `</root>` tag:

```xml
  <data name="Budget_Exhausted_Message" xml:space="preserve">
    <value>Ihr monatliches Budget ist aufgebraucht.</value>
  </data>
  <data name="Budget_FallbackModel_Warning" xml:space="preserve">
    <value>Budget überschritten. Gewechselt auf {0}.</value>
  </data>
```

- [ ] **Step 3: Add French keys**

In `Application/adessoGPT.Application/Localization/ErrorMessages.fr.resx`, add before the closing `</root>` tag:

```xml
  <data name="Budget_Exhausted_Message" xml:space="preserve">
    <value>Your monthly budget has been exhausted.</value>
  </data>
  <data name="Budget_FallbackModel_Warning" xml:space="preserve">
    <value>Budget exceeded. Switched to {0}.</value>
  </data>
```

- [ ] **Step 4: Add Italian keys**

In `Application/adessoGPT.Application/Localization/ErrorMessages.it.resx`, add before the closing `</root>` tag:

```xml
  <data name="Budget_Exhausted_Message" xml:space="preserve">
    <value>Your monthly budget has been exhausted.</value>
  </data>
  <data name="Budget_FallbackModel_Warning" xml:space="preserve">
    <value>Budget exceeded. Switched to {0}.</value>
  </data>
```

- [ ] **Step 5: Commit**

```bash
git add Application/adessoGPT.Application/Localization/ErrorMessages*.resx
git commit -m "feat(budget): add localization keys for budget exhausted and fallback warning"
```

---

### Task 4: Create IBudgetGuardService and BudgetGuardService

**Files:**
- Create: `Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs`
- Create: `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`

- [ ] **Step 1: Create the interface and types**

Create `Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs`:

```csharp
namespace adessoGPT.Application.Business.Budget.Services;

using adessoGPT.Chat.Abstractions.Streaming;
using adessoGPT.Domain.PersistedEntities.System.Settings.ModelOptions;

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
    public string? FallbackModelTitle { get; init; }
}

public interface IBudgetGuardService
{
    Task<BudgetCheckResult> CheckBudgetAsync(ChatStreamContext context, CancellationToken cancellationToken);
}
```

- [ ] **Step 2: Create the implementation**

Create `Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`:

```csharp
namespace adessoGPT.Application.Business.Budget.Services;

using adessoGPT.Application.Business.Agents.GetAgentEntity;
using adessoGPT.Chat.Abstractions.Streaming;
using adessoGPT.Domain;
using adessoGPT.Domain.PersistedEntities.Budget;
using adessoGPT.Domain.PersistedEntities.System.Settings.ModelOptions;
using MediatR;
using Microsoft.EntityFrameworkCore;

internal class BudgetGuardService : IBudgetGuardService
{
    private const long MonthlyTokenCap = 100_000;

    private readonly IUserDbContext _dbContext;
    private readonly IMediator _mediator;

    public BudgetGuardService(IUserDbContext dbContext, IMediator mediator)
    {
        _dbContext = dbContext;
        _mediator = mediator;
    }

    public async Task<BudgetCheckResult> CheckBudgetAsync(
        ChatStreamContext context,
        CancellationToken cancellationToken
    )
    {
        var budgetStateId = UserBudgetStateId.ForPeriod(BudgetPeriod.Monthly);

        var state = await _dbContext
            .BudgetStates.AsNoTracking()
            .FirstOrDefaultAsync(b => b.Id == budgetStateId, cancellationToken);

        if (state is null || state.TokensUsed < MonthlyTokenCap)
        {
            return new BudgetCheckResult { Outcome = BudgetCheckOutcome.Allowed };
        }

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
            var fallbackModelTitle = await GetModelTitle(fallbackConfig.ModelOptionsId, cancellationToken);

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

    private async Task<string> GetModelTitle(ModelOptionsId modelOptionsId, CancellationToken cancellationToken)
    {
        var systemDbContext = _dbContext as ISystemDbContext;

        if (systemDbContext is null)
        {
            return modelOptionsId.Value;
        }

        var modelOptions = await systemDbContext
            .ModelOptions.AsNoTracking()
            .FirstOrDefaultAsync(m => m.Id == modelOptionsId, cancellationToken);

        return modelOptions?.Title.DefaultTemplate ?? modelOptionsId.Value;
    }
}
```

**Note:** The `GetModelTitle` method resolves the display title for the fallback model. If `ISystemDbContext` is not available (which it should be in the shared DB context), it falls back to the raw ID string.

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`
Expected: Build succeeded, 0 errors.

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application/Business/Budget/Services/IBudgetGuardService.cs
git add Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs
git commit -m "feat(budget): add IBudgetGuardService with hardcoded monthly cap"
```

---

### Task 5: Register IBudgetGuardService in DI

**Files:**
- Modify: `Application/adessoGPT.Application/ApplicationModule.cs`

- [ ] **Step 1: Add registration**

In `Application/adessoGPT.Application/ApplicationModule.cs`, add the using and registration. Add the using statement:

```csharp
using adessoGPT.Application.Business.Budget.Services;
```

Add after line 59 (`services.AddScoped<IChatStreamRuntimeFactory, ChatStreamRuntimeFactory>();`):

```csharp
services.AddScoped<IBudgetGuardService, BudgetGuardService>();
```

- [ ] **Step 2: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`
Expected: Build succeeded, 0 errors.

- [ ] **Step 3: Commit**

```bash
git add Application/adessoGPT.Application/ApplicationModule.cs
git commit -m "feat(budget): register IBudgetGuardService in DI"
```

---

### Task 6: Integrate budget guard into StartChatConversationCommandHandler

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Chat/StartChatConversation/StartChatConversationCommandHandler.cs`

- [ ] **Step 1: Add budget guard to constructor and usings**

Add usings:
```csharp
using adessoGPT.Application.Business.Budget.Services;
using adessoGPT.Application.Business.Conversations.UpdateConversationModel;
using adessoGPT.Application.Localization;
using adessoGPT.Core.Localization;
```

Change the constructor to inject `IBudgetGuardService`:

```csharp
internal class StartChatConversationCommandHandler
    : ICommandHandler<StartChatConversationCommand, IAsyncEnumerable<ChatStreamResponse>>
{
    private readonly IMediator _mediator;
    private readonly IBudgetGuardService _budgetGuard;

    public StartChatConversationCommandHandler(IMediator mediator, IBudgetGuardService budgetGuard)
    {
        _mediator = mediator;
        _budgetGuard = budgetGuard;
    }
```

- [ ] **Step 2: Add budget check between context creation and stream creation**

Replace the section from after `chatStreamContextResult` success check to the `CreateChatStreamQuery` call. The existing code at lines 58-63:

```csharp
        // --- existing code up to chatStreamContextResult.IsFailure check ---

        var chatStreamContext = chatStreamContextResult.Value;

        var budgetResult = await _budgetGuard.CheckBudgetAsync(chatStreamContext, cancellationToken);

        if (budgetResult.Outcome == BudgetCheckOutcome.Blocked)
        {
            return BudgetBlockedStream(chatStreamContext);
        }

        if (budgetResult.Outcome == BudgetCheckOutcome.FallbackModel)
        {
            await _mediator.Send(
                new UpdateConversationModelCommand
                {
                    ConversationId = conversationResult.Value.Conversation.Id,
                    ModelOptionsId = budgetResult.FallbackModelOptionsId!.Value,
                },
                cancellationToken
            );

            var contextQuery = new CreateChatStreamContextQuery
            {
                ChatPromptMessage = conversationResult.Value.Message!,
                ConversationId = conversationResult.Value.Conversation.Id,
            };

            chatStreamContextResult = await _mediator.Send(contextQuery, cancellationToken);

            if (chatStreamContextResult.IsFailure)
            {
                return chatStreamContextResult.Error;
            }

            chatStreamContext = chatStreamContextResult.Value;

            chatStreamContext.PublishResponseToChatStream(
                new ChatBudgetWarningResponse
                {
                    Message = string.Format(
                        LocalizedString.For(ErrorMessages.Budget_FallbackModel_Warning),
                        budgetResult.FallbackModelTitle
                    ),
                    FallbackModelTitle = budgetResult.FallbackModelTitle ?? string.Empty,
                }
            );
        }

        var chatStreamResult = await _mediator.Send(
            new CreateChatStreamQuery { ChatStreamContext = chatStreamContext },
            cancellationToken
        );
```

Add a private helper method at the end of the class:

```csharp
    private static IAsyncEnumerable<ChatStreamResponse> BudgetBlockedStream(ChatStreamContext context)
    {
        context.PublishResponseToChatStream(
            new ChatBudgetExhaustedResponse
            {
                Message = LocalizedString.For(ErrorMessages.Budget_Exhausted_Message),
            }
        );

        return AsyncEnumerable.Empty<ChatStreamResponse>();
    }
```

**Important:** The `ChatConversationCreatedResponse` publish block (lines 65-78) must use `chatStreamContext` (not `chatStreamContextResult.Value`) so it references the potentially rebuilt context.

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`
Expected: Build succeeded, 0 errors.

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application/Business/Chat/StartChatConversation/StartChatConversationCommandHandler.cs
git commit -m "feat(budget): integrate budget guard into StartChatConversationCommandHandler"
```

---

### Task 7: Integrate budget guard into ResumeChatConversationCommandHandler

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Chat/ResumeChatConversation/ResumeChatConversationCommandHandler.cs`

- [ ] **Step 1: Add budget guard to constructor and usings**

Add usings:
```csharp
using adessoGPT.Application.Business.Budget.Services;
using adessoGPT.Application.Business.Conversations.UpdateConversationModel;
using adessoGPT.Application.Localization;
using adessoGPT.Chat.Abstractions.Streaming.Updates;
using adessoGPT.Core.Localization;
```

Add `IBudgetGuardService` to constructor:

```csharp
    private readonly IMediator _mediator;
    private readonly TimeProvider _timeProvider;
    private readonly IUserDbContext _dbContext;
    private readonly IBudgetGuardService _budgetGuard;

    public ResumeChatConversationCommandHandler(
        IMediator mediator,
        TimeProvider timeProvider,
        IUserDbContext dbContext,
        IBudgetGuardService budgetGuard
    )
    {
        _mediator = mediator;
        _timeProvider = timeProvider;
        _dbContext = dbContext;
        _budgetGuard = budgetGuard;
    }
```

- [ ] **Step 2: Add budget check between context creation and stream creation**

After the `chatStreamContextResult.IsFailure` check (line 122) and before the `CreateChatStreamQuery` call (line 125), insert:

```csharp
        var chatStreamContext = chatStreamContextResult.Value;

        var budgetResult = await _budgetGuard.CheckBudgetAsync(chatStreamContext, cancellationToken);

        if (budgetResult.Outcome == BudgetCheckOutcome.Blocked)
        {
            return BudgetBlockedStream(chatStreamContext);
        }

        if (budgetResult.Outcome == BudgetCheckOutcome.FallbackModel)
        {
            await _mediator.Send(
                new UpdateConversationModelCommand
                {
                    ConversationId = command.ConversationId,
                    ModelOptionsId = budgetResult.FallbackModelOptionsId!.Value,
                },
                cancellationToken
            );

            chatStreamContextResult = await _mediator.Send(
                new CreateChatStreamContextQuery
                {
                    ChatPromptMessage = userMessage,
                    ConversationId = command.ConversationId,
                },
                cancellationToken
            );

            if (chatStreamContextResult.IsFailure)
            {
                return chatStreamContextResult.Error;
            }

            chatStreamContext = chatStreamContextResult.Value;

            chatStreamContext.PublishResponseToChatStream(
                new ChatBudgetWarningResponse
                {
                    Message = string.Format(
                        LocalizedString.For(ErrorMessages.Budget_FallbackModel_Warning),
                        budgetResult.FallbackModelTitle
                    ),
                    FallbackModelTitle = budgetResult.FallbackModelTitle ?? string.Empty,
                }
            );
        }

        var chatStreamResult = await _mediator.Send(
            new CreateChatStreamQuery { ChatStreamContext = chatStreamContext },
            cancellationToken
        );

        return chatStreamResult;
```

Also add the `BudgetBlockedStream` private static helper method (same as Task 6) at the end of the class:

```csharp
    private static IAsyncEnumerable<ChatStreamResponse> BudgetBlockedStream(ChatStreamContext context)
    {
        context.PublishResponseToChatStream(
            new ChatBudgetExhaustedResponse
            {
                Message = LocalizedString.For(ErrorMessages.Budget_Exhausted_Message),
            }
        );

        return AsyncEnumerable.Empty<ChatStreamResponse>();
    }
```

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application/Business/Chat/ResumeChatConversation/ResumeChatConversationCommandHandler.cs
git commit -m "feat(budget): integrate budget guard into ResumeChatConversationCommandHandler"
```

---

### Task 8: Integrate budget guard into RegenerateAssistantChatMessageCommandHandler

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Chat/RegenerateAssistantChatMessage/RegenerateAssistantChatMessageCommandHandler.cs`

- [ ] **Step 1: Add budget guard to constructor and usings**

Add usings:
```csharp
using adessoGPT.Application.Business.Budget.Services;
using adessoGPT.Application.Business.Conversations.UpdateConversationModel;
using adessoGPT.Application.Localization;
using adessoGPT.Core.Localization;
```

Add `IBudgetGuardService` to constructor:

```csharp
    private readonly IUserDbContext _dbContext;
    private readonly IMediator _mediator;
    private readonly IBudgetGuardService _budgetGuard;

    public RegenerateAssistantChatMessageCommandHandler(
        IUserDbContext dbContext,
        IMediator mediator,
        IBudgetGuardService budgetGuard
    )
    {
        _dbContext = dbContext;
        _mediator = mediator;
        _budgetGuard = budgetGuard;
    }
```

- [ ] **Step 2: Add budget check between context creation and stream creation**

After `chatStreamContextResult.IsFailure` check (line 99) and before `CreateChatStreamQuery` call (line 102), insert the same budget guard pattern. Key difference: the `CreateChatStreamContextQuery` includes a `ChatMessageFilter`, so the re-query must preserve it:

```csharp
        var chatStreamContext = chatStreamContextResult.Value;

        var budgetResult = await _budgetGuard.CheckBudgetAsync(chatStreamContext, cancellationToken);

        if (budgetResult.Outcome == BudgetCheckOutcome.Blocked)
        {
            return BudgetBlockedStream(chatStreamContext);
        }

        if (budgetResult.Outcome == BudgetCheckOutcome.FallbackModel)
        {
            await _mediator.Send(
                new UpdateConversationModelCommand
                {
                    ConversationId = command.ConversationId,
                    ModelOptionsId = budgetResult.FallbackModelOptionsId!.Value,
                },
                cancellationToken
            );

            chatStreamContextResult = await _mediator.Send(
                new CreateChatStreamContextQuery
                {
                    ChatPromptMessage = userMessageToPrompt,
                    ConversationId = command.ConversationId,
                    ChatMessageFilter = message =>
                    {
                        if (message.Id == command.MessageId)
                        {
                            return false;
                        }

                        return message.CreatedAt < messageToRegenerate.CreatedAt;
                    },
                },
                cancellationToken
            );

            if (chatStreamContextResult.IsFailure)
            {
                return chatStreamContextResult.Error;
            }

            chatStreamContext = chatStreamContextResult.Value;

            chatStreamContext.PublishResponseToChatStream(
                new ChatBudgetWarningResponse
                {
                    Message = string.Format(
                        LocalizedString.For(ErrorMessages.Budget_FallbackModel_Warning),
                        budgetResult.FallbackModelTitle
                    ),
                    FallbackModelTitle = budgetResult.FallbackModelTitle ?? string.Empty,
                }
            );
        }

        var chatStreamResult = await _mediator.Send(
            new CreateChatStreamQuery { ChatStreamContext = chatStreamContext },
            cancellationToken
        );

        return chatStreamResult;
```

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application/Business/Chat/RegenerateAssistantChatMessage/RegenerateAssistantChatMessageCommandHandler.cs
git commit -m "feat(budget): integrate budget guard into RegenerateAssistantChatMessageCommandHandler"
```

---

### Task 9: Integrate budget guard into ChangeUserChatMessageCommandHandler

**Files:**
- Modify: `Application/adessoGPT.Application/Business/Chat/ChangeUserChatMessage/ChangeUserChatMessageCommandHandler.cs`

- [ ] **Step 1: Add budget guard to constructor and usings**

Add usings:
```csharp
using adessoGPT.Application.Business.Budget.Services;
using adessoGPT.Application.Business.Conversations.UpdateConversationModel;
using adessoGPT.Application.Localization;
using adessoGPT.Chat.Abstractions.Streaming.Updates;
using adessoGPT.Core.Localization;
```

Add `IBudgetGuardService` to constructor:

```csharp
    private readonly IUserDbContext _dbContext;
    private readonly IMediator _mediator;
    private readonly TimeProvider _timeProvider;
    private readonly IBudgetGuardService _budgetGuard;

    public ChangeUserChatMessageCommandHandler(
        IUserDbContext dbContext,
        IMediator mediator,
        TimeProvider timeProvider,
        IBudgetGuardService budgetGuard
    )
    {
        _dbContext = dbContext;
        _mediator = mediator;
        _timeProvider = timeProvider;
        _budgetGuard = budgetGuard;
    }
```

- [ ] **Step 2: Add budget check between context creation and stream creation**

After `chatStreamContextResult.IsFailure` check (line 108) and before `CreateChatStreamQuery` (line 111), insert:

```csharp
        var chatStreamContext = chatStreamContextResult.Value;

        var budgetResult = await _budgetGuard.CheckBudgetAsync(chatStreamContext, cancellationToken);

        if (budgetResult.Outcome == BudgetCheckOutcome.Blocked)
        {
            return BudgetBlockedStream(chatStreamContext);
        }

        if (budgetResult.Outcome == BudgetCheckOutcome.FallbackModel)
        {
            await _mediator.Send(
                new UpdateConversationModelCommand
                {
                    ConversationId = command.ConversationId,
                    ModelOptionsId = budgetResult.FallbackModelOptionsId!.Value,
                },
                cancellationToken
            );

            chatStreamContextResult = await _mediator.Send(
                new CreateChatStreamContextQuery
                {
                    ChatPromptMessage = newUserMessage,
                    ConversationId = command.ConversationId,
                },
                cancellationToken
            );

            if (chatStreamContextResult.IsFailure)
            {
                return chatStreamContextResult.Error;
            }

            chatStreamContext = chatStreamContextResult.Value;

            chatStreamContext.PublishResponseToChatStream(
                new ChatBudgetWarningResponse
                {
                    Message = string.Format(
                        LocalizedString.For(ErrorMessages.Budget_FallbackModel_Warning),
                        budgetResult.FallbackModelTitle
                    ),
                    FallbackModelTitle = budgetResult.FallbackModelTitle ?? string.Empty,
                }
            );
        }

        var chatStreamResult = await _mediator.Send(
            new CreateChatStreamQuery { ChatStreamContext = chatStreamContext },
            cancellationToken
        );

        return chatStreamResult;
```

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application/Business/Chat/ChangeUserChatMessage/ChangeUserChatMessageCommandHandler.cs
git commit -m "feat(budget): integrate budget guard into ChangeUserChatMessageCommandHandler"
```

---

### Task 10: Integrate budget guard into StartRealtimeChatConversationCommandHandler

**Files:**
- Modify: `Application/adessoGPT.Application.Realtime/Business/Chat/StartChatConversation/StartRealtimeChatConversationCommandHandler.cs`

- [ ] **Step 1: Add budget guard to constructor and usings**

Add usings:
```csharp
using adessoGPT.Application.Business.Budget.Services;
using adessoGPT.Application.Business.Conversations.UpdateConversationModel;
using adessoGPT.Application.Localization;
using adessoGPT.Application.Realtime.Business.Chat.ChatStreaming.CreateChatStreamContext;
using adessoGPT.Chat.Abstractions.Streaming.Updates;
using adessoGPT.Core.Localization;
```

Add `IBudgetGuardService` to constructor:

```csharp
    private readonly IMediator _mediator;
    private readonly IBudgetGuardService _budgetGuard;

    public StartRealtimeChatConversationCommandHandler(IMediator mediator, IBudgetGuardService budgetGuard)
    {
        _mediator = mediator;
        _budgetGuard = budgetGuard;
    }
```

- [ ] **Step 2: Add budget check between context creation and stream creation**

After `chatStreamContextResult.IsFailure` check (line 54) and before `CreateRealtimeChatStreamQuery` (line 57), insert:

```csharp
        var chatStreamContext = chatStreamContextResult.Value;

        var budgetResult = await _budgetGuard.CheckBudgetAsync(chatStreamContext, cancellationToken);

        if (budgetResult.Outcome == BudgetCheckOutcome.Blocked)
        {
            return BudgetBlockedStream(chatStreamContext);
        }

        if (budgetResult.Outcome == BudgetCheckOutcome.FallbackModel)
        {
            await _mediator.Send(
                new UpdateConversationModelCommand
                {
                    ConversationId = conversationResult.Value.Conversation.Id,
                    ModelOptionsId = budgetResult.FallbackModelOptionsId!.Value,
                },
                cancellationToken
            );

            chatStreamContextResult = await _mediator.Send(
                new CreateRealtimeChatStreamContextQuery
                {
                    ConversationId = conversationResult.Value.Conversation.Id,
                    InputStream = command.InputStream,
                    Message = conversationResult.Value.Message,
                },
                cancellationToken
            );

            if (chatStreamContextResult.IsFailure)
            {
                return chatStreamContextResult.Error;
            }

            chatStreamContext = chatStreamContextResult.Value;

            chatStreamContext.PublishResponseToChatStream(
                new ChatBudgetWarningResponse
                {
                    Message = string.Format(
                        LocalizedString.For(ErrorMessages.Budget_FallbackModel_Warning),
                        budgetResult.FallbackModelTitle
                    ),
                    FallbackModelTitle = budgetResult.FallbackModelTitle ?? string.Empty,
                }
            );
        }

        var chatStreamResult = await _mediator.Send(
            new CreateRealtimeChatStreamQuery { ChatStreamContext = chatStreamContext },
            cancellationToken
        );
```

**Important:** The `ChatConversationCreatedResponse` publish block must use `chatStreamContext` (not `chatStreamContextResult.Value`).

- [ ] **Step 3: Build to verify**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`

- [ ] **Step 4: Commit**

```bash
git add Application/adessoGPT.Application.Realtime/Business/Chat/StartChatConversation/StartRealtimeChatConversationCommandHandler.cs
git commit -m "feat(budget): integrate budget guard into StartRealtimeChatConversationCommandHandler"
```

---

### Task 11: Final build, format, and verify

- [ ] **Step 1: Full build**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app && dotnet build`
Expected: Build succeeded, 0 errors.

- [ ] **Step 2: Format**

Run: `cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Backend && dotnet csharpier format .`

- [ ] **Step 3: Commit formatting if changed**

```bash
git add -A
git commit -m "style: format with CSharpier"
```
