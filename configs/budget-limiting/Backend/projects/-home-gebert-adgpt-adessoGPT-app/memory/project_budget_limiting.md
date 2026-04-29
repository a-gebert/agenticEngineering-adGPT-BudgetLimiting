---
name: Budget Limiting Implementation
description: PBI3271 Budget Limits — Tier-based usage limits and budgets for adessoGPT, concept v2, architecture decisions, codebase integration points, and current implementation state
type: project
originSessionId: 925c1da2-e0cf-4ed2-aaa1-f053889fead4
---
# Budget Limiting — PBI3271

**Branch:** feature/PBI3271_Budget_Limits
**Working directory:** /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Backend
**Concept:** agenticEngineering-adGPT-BudgetLimiting/configs/Backend/docs/adessogpt-budgetierung-konzept-v2_1.md (read-only)
**Status:** Walking skeleton in progress — entity, CQRS commands, and chat-stream integration done

## Core Architecture

Tier-based model (Restricted/Standard/Power) with Entra-ID group mapping. All data in existing Cosmos containers `user` and `system`. No new Azure services.

**Why:** Controlled, cost-efficient platform usage. Admins configure via Entra group membership (no separate budget admin UI initially).

**How to apply:** Every implementation decision must stay within the existing container/infrastructure boundary. New document types use `$type` discriminator pattern.

## Implemented So Far

### Entity: UserBudgetState
- `Shared/adessoGPT.Domain/PersistedEntities/Budget/UserBudgetState.cs`
- Extends `UserPartitionedEntity` (user container, PK: UserId)
- Composite ID via `UserBudgetStateId.ForPeriod(userId, periodStart, period)` → e.g. `budget-{guid}-2026-04`
- Fields: `TokensUsed`, `CostUsd`, `RequestCount`, `LastRecordedAt`
- Supports `BudgetPeriod.Monthly`, `Weekly`, `Daily`
- `DbSet<UserBudgetState> BudgetStates` added to `IUserDbContext`
- EF configurations in InMemory + MongoDb + CosmosDb persistence projects

### CQRS Commands (Application layer)

**High-level (chat integration):**
- `RecordChatBudgetUsageCommand` — takes `TokensUsed` + `CostUsd`, handler resolves user via `IUserAccessor`, iterates Daily→Weekly→Monthly, ensures each `UserBudgetState` exists (upsert), increments all counters, single `SaveChangesAsync`
  - `Application/Business/Budget/RecordChatBudgetUsage/`

**Low-level (building blocks):**
- `EnsureBudgetStateCommand` — ensures a single-period `UserBudgetState` exists for current user
  - `Application/Business/Budget/EnsureBudgetState/`
- `RecordBudgetUsageCommand` — increments a single `UserBudgetState` by ID (for admin/manual use)
  - `Application/Business/Budget/RecordBudgetUsage/`

**Queries:**
- `GetBudgetStateQuery` — reads budget state for current user
  - `Application/Business/Budget/GetBudgetState/`
- `GetBudgetUsageReportQuery` (ControlCenter) — admin reporting
  - `Application/adessoGPT.Application.ControlCenter/Business/Budget/GetBudgetUsageReport/`

**Endpoints:**
- `BudgetEndpoints.cs` — user-facing budget endpoints
- `BudgetAdminEndpoints.cs` — admin budget endpoints

### Chat Stream Integration

Both `ChatStreamPersistingWrapper` classes (standard + realtime) record budget usage after successful message persistence:

```
ChatStreamPersistingWrapper
  → ITokenCounter.CountTokensWithFallbackModelAsDefault(prompt + response)
  → sends RecordChatBudgetUsageCommand { TokensUsed, CostUsd: 0m }
    → Handler: foreach (Daily, Weekly, Monthly) → ensure + increment → SaveChanges
```

- Standard wrapper: `Application/adessoGPT.Application/Business/Chat/ChatStreaming/CreateChatStream/ChatStreamWrappers/ChatStreamPersistingWrapper.cs`
- Realtime wrapper: `Application/adessoGPT.Application.Realtime/Business/Chat/ChatStreaming/CreateChatStream/ChatStreamWrappers/ChatStreamPersistingWrapper.cs`
- Both use `ITokenCounter` + `ILogger` (added to constructor)
- Error handling: try-catch swallows all exceptions, logs warning/error — never breaks the chat stream
- CostUsd is 0m dummy — ModelPricing not yet implemented

### Design Decision: Wrapper stays thin
The wrapper only estimates tokens and sends one command. All period logic (daily→weekly→monthly), user resolution, and ensure/upsert logic lives in `RecordChatBudgetUsageCommandHandler`. This was an explicit refactoring from an earlier version that had too much logic in the wrapper.

## Key Integration Points (remaining)

- **PreCheck**: Before Azure OpenAI call in chat flow (not yet implemented)
- **Tier Resolution**: UserAccessor.GetUserGroups() → GroupId-Claims from JWT → BudgetTierMapping → lowest Priority wins (not yet implemented)
- **ChatSessionAuditEntry**: Referenced in concept but does NOT exist yet in PBI3271 branch — needs to be created or merged from PBI3270

## New Document Types (planned, not all implemented)

- `UserBudgetState` ✅ (user container, PK: UserId) — per-user per-period counters
- `RateLimitWindow` (user container, PK: UserId) — RPM counter with TTL 120s
- `BudgetTier` (system container, SystemScope: BudgetConfiguration) — tier definitions
- `BudgetTierMapping` (system container, SystemScope: BudgetConfiguration) — group→tier mapping
- `ModelPricing` (system container, SystemScope: BudgetConfiguration) — model price table
- `FxRate` (system container, SystemScope: BudgetConfiguration) — daily USD→EUR rate

## Etappen

1. Walking Skeleton (seed docs, tier resolver, budget state, precheck, record, test endpoint) ← **in progress**
2. MVP (token estimator, cost calculator, rate limiting, audit extension, streaming, frontend banner)
3. Production-Ready (FX worker, reconciliation, telemetry, load tests, feature flag)
4. Reporting & Admin (dashboard, export, optional admin UI)
