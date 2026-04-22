---
name: Budget Limiting Implementation
description: PBI3271 Budget Limits — Tier-based usage limits and budgets for adessoGPT, concept v2, architecture decisions, and codebase integration points
type: project
originSessionId: 925c1da2-e0cf-4ed2-aaa1-f053889fead4
---
# Budget Limiting — PBI3271

**Branch:** feature/PBI3271_Budget_Limits
**Concept:** agenticEngineering-adGPT-BudgetLimiting/configs/Backend/docs/adessogpt-budgetierung-konzept-v2_1.md (read-only)
**Status:** Concept finalized, implementation not started

## Core Architecture

Tier-based model (Restricted/Standard/Power) with Entra-ID group mapping. All data in existing Cosmos containers `user` and `system`. No new Azure services.

**Why:** Controlled, cost-efficient platform usage. Admins configure via Entra group membership (no separate budget admin UI initially).

**How to apply:** Every implementation decision must stay within the existing container/infrastructure boundary. New document types use `$type` discriminator pattern.

## Key Integration Points

- **PreCheck**: Before Azure OpenAI call in chat flow (StartChatConversationCommandHandler or pipeline behavior)
- **Record**: After Azure OpenAI response in ChatStreamPersistingWrapper (both standard and realtime)
- **Tier Resolution**: UserAccessor.GetUserGroups() → GroupId-Claims from JWT → BudgetTierMapping → lowest Priority wins
- **ChatSessionAuditEntry**: Referenced in concept but does NOT exist yet in PBI3271 branch — needs to be created or merged from PBI3270

## New Document Types

- `UserBudgetState` (user container, PK: UserId) — per-user per-period counters
- `RateLimitWindow` (user container, PK: UserId) — RPM counter with TTL 120s
- `BudgetTier` (system container, SystemScope: BudgetConfiguration) — tier definitions
- `BudgetTierMapping` (system container, SystemScope: BudgetConfiguration) — group→tier mapping
- `ModelPricing` (system container, SystemScope: BudgetConfiguration) — model price table
- `FxRate` (system container, SystemScope: BudgetConfiguration) — daily USD→EUR rate

## Etappen

1. Walking Skeleton (seed docs, tier resolver, budget state, precheck, record, test endpoint)
2. MVP (token estimator, cost calculator, rate limiting, audit extension, streaming, frontend banner)
3. Production-Ready (FX worker, reconciliation, telemetry, load tests, feature flag)
4. Reporting & Admin (dashboard, export, optional admin UI)
