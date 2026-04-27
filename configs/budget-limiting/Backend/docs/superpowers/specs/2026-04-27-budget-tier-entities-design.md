# BudgetTier ControlCenter Entities Design

**Date:** 2026-04-27
**Status:** Approved
**Scope:** Domain entities, CQRS endpoints, repository, persistence, and tier resolution for the BudgetTier ControlCenter feature.

---

## 1. Overview

Admins can create arbitrary BudgetTiers via the ControlCenter. Each tier defines token limits per period (daily, weekly, monthly), a priority for conflict resolution, and is assigned to exactly one user group. A default tier covers users not matched to any group. `null` limit values represent unlimited budget for that period.

This spec covers the entity model, CQRS endpoints, repository/caching, persistence, audit integration, and the tier resolution service. It does **not** cover the BudgetGuardService refactoring to consume tiers — that is a separate implementation step.

---

## 2. Domain Entities

### 2.1 BudgetTier (new, collection entity)

Inherits from `SystemSettingsPartitionedEntity` (implements `ISystemSetting`, `IAuditableEntity`).

```csharp
public readonly partial struct BudgetTierId { }

public record BudgetTier : SystemSettingsPartitionedEntity
{
    public required BudgetTierId Id { get; init; }
    public required LocalizationStrings Title { get; init; }
    public required LocalizationStrings Description { get; init; }
    public required int Priority { get; init; }
    public bool IsDefault { get; init; }

    // 1:1 group assignment (null = default/unassigned tier)
    public UserGroupMappingId? AssignedUserGroupId { get; init; }

    // Daily token limit (null = unlimited)
    public long? DailyTokenLimit { get; init; }

    // Weekly token limit (null = unlimited)
    public long? WeeklyTokenLimit { get; init; }

    // Monthly token limit (null = unlimited)
    public long? MonthlyTokenLimit { get; init; }

    // Requests per minute (null = unlimited, prepared for later use)
    public int? RequestsPerMinute { get; init; }

    // Warning threshold percentage (default 80)
    public int SoftWarningPercent { get; init; } = 80;
}
```

**Key decisions:**

| Decision | Rationale |
|----------|-----------|
| Flat limit properties | Exactly 3 periods, 1 dimension each — no abstraction needed |
| `null` = unlimited | Idiomatic C#, simple enforcement check (`if limit is null → skip`) |
| `UserGroupMappingId?` for group ref | Consistent with Agent, ModelOptions, DataSource patterns |
| `Priority` int, lowest wins | Concept v2.1 conflict resolution rule preserved |
| No `AllowedModelIds` | Out of scope — model restrictions handled elsewhere |
| No `CostLimitUsd` | Costs are estimated with fixed factor from token usage |
| `RequestsPerMinute` prepared | Field exists but enforcement deferred to a later step |

**Strongly-typed ID:** `BudgetTierId` is a string-based strongly-typed ID, generated as `Guid.NewGuid().ToString()`.

**Cosmos container:** `system`, with `SystemScope = "Settings"` (inherited partition scope).

### 2.2 BudgetLimitSettings (existing, extended)

The existing `SingleSystemSettingsBase` entity gains one new field:

```csharp
public record BudgetLimitSettings : SingleSystemSettingsBase, ...
{
    public bool IsEnabled { get; init; } = true;
    public long? MonthlyTokenLimit { get; init; } = 500;  // legacy, kept for backward compat
    public BudgetTierId? DefaultBudgetTierId { get; init; }  // NEW
}
```

`DefaultBudgetTierId` is a denormalized reference for fast lookup. The source of truth is `BudgetTier.IsDefault`.

---

## 3. CQRS Endpoints & Handlers

### 3.1 API Endpoints

All require `UserRoles.ControlCenterAdmin`.

```
GET    /api/control-center/budget-tiers              → GetControlCenterBudgetTiersQuery
GET    /api/control-center/budget-tiers/{id}          → GetControlCenterBudgetTierQuery
POST   /api/control-center/budget-tiers               → CreateControlCenterBudgetTierCommand
PUT    /api/control-center/budget-tiers/{id}           → UpdateControlCenterBudgetTierCommand
DELETE /api/control-center/budget-tiers/{id}           → DeleteControlCenterBudgetTierCommand
PUT    /api/control-center/budget-tiers/{id}/default   → SetControlCenterDefaultBudgetTierCommand
```

### 3.2 Command Handlers

**CreateControlCenterBudgetTierCommand:**
- Generates `BudgetTierId` as `Guid.NewGuid().ToString()`
- Validates all fields (see validation rules below)
- If `IsDefault = true`, clears `IsDefault` on all existing tiers (Agent pattern)
- Updates `BudgetLimitSettings.DefaultBudgetTierId`
- Returns the created `BudgetTierId`

**UpdateControlCenterBudgetTierCommand:**
- Uses `with` expression pattern (UserGroupMapping pattern)
- Same validations as create
- If changing `IsDefault` to true, clears other defaults and updates `BudgetLimitSettings`

**DeleteControlCenterBudgetTierCommand:**
- Cannot delete the default tier (returns error)
- Removes the tier
- Clears `BudgetLimitSettings.DefaultBudgetTierId` if it referenced this tier

**SetControlCenterDefaultBudgetTierCommand:**
- Dedicated endpoint (Agent's `SetControlCenterDefaultAgentCommand` pattern)
- Clears `IsDefault` on all other tiers, sets it on the target
- Updates `BudgetLimitSettings.DefaultBudgetTierId`

### 3.3 Query Handlers

**GetControlCenterBudgetTiersQuery:**
- Returns all tiers with full details
- Includes resolved group name (`Title` from `UserGroupMapping`) for UI display

**GetControlCenterBudgetTierQuery:**
- Single tier by ID, 404 if not found

### 3.4 Validation Rules

| Field | Rule |
|-------|------|
| `Title` | Required, valid `LocalizationStrings` (en key required, non-empty) |
| `Description` | Required, valid `LocalizationStrings` (en key required, non-empty) |
| `Priority` | Required, > 0 |
| `SoftWarningPercent` | 1-100, default 80 |
| `DailyTokenLimit` | null or > 0 |
| `WeeklyTokenLimit` | null or > 0 |
| `MonthlyTokenLimit` | null or > 0 |
| `RequestsPerMinute` | null or > 0 |
| `AssignedUserGroupId` | null, or must exist in UserGroupRepository AND must not be assigned to another tier |

---

## 4. Repository & Caching

### 4.1 Repository Interface

```csharp
public interface IBudgetTierRepository
    : ISystemSettingRepository<BudgetTier, BudgetTierId> { }
```

### 4.2 Implementation

```csharp
internal class BudgetTierRepository
    : SystemSettingCachedRepositoryBase<BudgetTier, BudgetTierId>,
      IBudgetTierRepository
{
    protected override BudgetTierId GetEntityId(BudgetTier entity) => entity.Id;

    protected override Expression<Func<BudgetTier, bool>> GetEntityByIdExpression(BudgetTierId id)
        => e => e.Id == id;
}
```

**Caching:** FusionCache with 1-hour TTL, auto-invalidated on any write. Multi-pod deployment supported via Redis-backed distributed cache invalidation.

### 4.3 DI Registration

```csharp
services.AddSystemSettingRepository<IBudgetTierRepository, BudgetTierRepository, BudgetTier, BudgetTierId>();
```

---

## 5. Persistence Configuration

Three EF Core configurations (Cosmos DB, MongoDB, In-Memory), all following the same pattern as `UserGroupMappingConfiguration`.

- **Cosmos DB:** Stored in the `system` container with `SystemScope = "Settings"`.
- **MongoDB:** Shared system settings collection.
- **In-Memory:** Standard EF Core in-memory provider for tests.

---

## 6. Audit Trail

`BudgetTier` implements `IAuditableEntity` via `SystemSettingsPartitionedEntity`. The `ConfigurationAuditInterceptor` automatically captures before/after snapshots on create, update, delete.

An `IAuditEntityConfiguration<BudgetTier>` defines tracked properties and display metadata, following the established pattern.

---

## 7. Tier Resolution Service

### 7.1 Interface

```csharp
public interface IBudgetTierResolver
{
    Task<BudgetTier?> ResolveForUserAsync(CancellationToken cancellationToken);
}
```

### 7.2 Resolution Algorithm

1. Extract `UserGroupId[]` from JWT via `UserAccessor.GetUserGroups()`
2. Load all `BudgetTier` entities from cache
3. Load all `UserGroupMapping` entities from cache
4. For each user group ID, find the `UserGroupMapping` with matching `ExternalGroupId`
5. For each matched `UserGroupMappingId`, find a `BudgetTier` with matching `AssignedUserGroupId`
6. If multiple tiers match: **lowest `Priority` wins** (most restrictive)
7. If no tiers match: return the tier where `IsDefault = true`
8. If no default tier exists: return `null` (budget feature effectively disabled for this user)

**Performance:** All data from FusionCache. No DB calls per request. Pure in-memory lookup.

---

## 8. Delete Cascades

### 8.1 Deleting a UserGroupMapping

The existing `DeleteControlCenterUserGroupCommandHandler` already cascades to Agents, DataSources, and Models. A new step is added: clear `AssignedUserGroupId` on any `BudgetTier` that referenced the deleted group (set to `null`).

### 8.2 Deleting a BudgetTier

- Cannot delete the tier marked `IsDefault = true`
- Clears `BudgetLimitSettings.DefaultBudgetTierId` if it referenced this tier
- No cascading to `UserBudgetState` — existing usage records remain valid (they don't reference the tier)

---

## 9. Relationship Diagram

```
BudgetLimitSettings (singleton, cached)
  ├── IsEnabled: bool
  ├── DefaultBudgetTierId ──→ BudgetTier.Id
  └── MonthlyTokenLimit (legacy)

BudgetTier (collection, cached, audited)
  ├── Id (BudgetTierId)
  ├── Title, Description (LocalizationStrings)
  ├── Priority (int, lowest = most restrictive)
  ├── IsDefault (bool)
  ├── AssignedUserGroupId ──→ UserGroupMapping.Id  (1:1, nullable)
  ├── DailyTokenLimit, WeeklyTokenLimit, MonthlyTokenLimit (long?, null = unlimited)
  ├── RequestsPerMinute (int?, prepared)
  └── SoftWarningPercent (int, default 80)

UserGroupMapping (existing, cached)
  ├── Id (UserGroupMappingId)
  ├── ExternalGroupId ──→ Entra ID group OID
  └── Title, Description (LocalizationStrings)

UserBudgetState (existing, per user per period)
  ├── TokensUsed, CostUsd, RequestCount
  └── PeriodStart, PeriodEnd
```

---

## 10. Out of Scope

- BudgetGuardService refactoring to consume tiers (separate step)
- Rate limiting enforcement (RequestsPerMinute field prepared but not enforced)
- ModelPricing entity (costs estimated with fixed factor)
- FxRate / EUR display (deferred)
- Frontend ControlCenter UI for BudgetTier CRUD (separate frontend spec)
