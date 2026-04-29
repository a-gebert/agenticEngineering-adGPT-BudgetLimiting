# BudgetTier Backend API — Frontend Summary

**Date:** 2026-04-27
**Status:** Backend implemented, API client regeneration pending

---

## Overview

Admins can now manage **Budget Tiers** (Budget-Stufen) via the ControlCenter. Each tier defines token limits per period and is assigned to a user group. A default tier covers users without group assignment.

---

## API Endpoints

Base path: `/api/control-center/budget-tiers`
Authorization: `ControlCenterAdmin` role required for all endpoints.

| Method | Route | Description | Request Body | Response |
|--------|-------|-------------|--------------|----------|
| `GET` | `/` | List all tiers (sorted by priority) | — | `{ budgetTiers: BudgetTierItem[] }` |
| `GET` | `/{id}` | Single tier by ID | — | `BudgetTierDetail` |
| `POST` | `/` | Create new tier | `BudgetTierDto` | `string` (new ID) |
| `PUT` | `/{id}` | Update existing tier | `{ id, budgetTier: BudgetTierDto }` | — |
| `DELETE` | `/{id}` | Delete tier (blocked if default) | — | — |
| `POST` | `/{id}/set-default` | Mark tier as default | — | — |

---

## Data Model

### BudgetTierDto (Create/Update Request Body)

```typescript
interface BudgetTierDto {
  title: LocalizationStrings;         // { en: "...", de: "..." } — required
  description: LocalizationStrings;   // { en: "...", de: "..." } — required
  priority: number;                   // > 0, lower = more restrictive
  assignedUserGroupId?: string;       // UserGroupMapping ID, null = unassigned
  dailyTokenLimit?: number;           // null = unlimited
  weeklyTokenLimit?: number;          // null = unlimited
  monthlyTokenLimit?: number;         // null = unlimited
  requestsPerMinute?: number;         // null = unlimited (prepared, not enforced yet)
  softWarningPercent: number;         // 1–100, default 80
}
```

### BudgetTierItem (List Response)

```typescript
interface BudgetTierItem {
  id: string;
  title: LocalizationStrings;
  description: LocalizationStrings;
  priority: number;
  isDefault: boolean;
  assignedUserGroupId?: string;
  assignedUserGroupTitle?: string;    // resolved display name of the group
  dailyTokenLimit?: number;
  weeklyTokenLimit?: number;
  monthlyTokenLimit?: number;
  requestsPerMinute?: number;
  softWarningPercent: number;
}
```

### BudgetTierDetail (Single Response)

Same as `BudgetTierItem` — inherits all DTO fields plus `id`, `isDefault`, `assignedUserGroupTitle`.

---

## Key UI Concepts

### Unlimited Budget

`null` on any limit field means **unlimited** for that period. The UI should represent this clearly (e.g., toggle, empty field, or "Unlimited" label).

### Default Tier

- Exactly one tier can be marked as default (via the `/set-default` endpoint).
- The default tier applies to users not matched to any specific group.
- The default tier cannot be deleted — the user must assign a different default first.

### User Group Assignment

- Each tier can be assigned to exactly **one** user group (`assignedUserGroupId`).
- Each user group can only be assigned to **one** tier (backend validates uniqueness).
- The list response includes `assignedUserGroupTitle` (already localized) for display.
- Use the existing UserGroupMapping list (`GET /api/control-center/user-groups`) for the group dropdown.

### Priority

- Integer > 0, lower value = more restrictive.
- Used for conflict resolution when a user belongs to multiple groups with different tiers.

### Warning Threshold

- `softWarningPercent` (1–100, default 80): percentage of budget usage at which users see a warning banner in the chat UI.

### Token Limits

Three independent period limits:
- **Daily** (`dailyTokenLimit`)
- **Weekly** (`weeklyTokenLimit`)
- **Monthly** (`monthlyTokenLimit`)

Each can be set independently. All are optional (null = unlimited).

---

## Validation Rules (Backend-enforced)

| Field | Rule |
|-------|------|
| `title` | Required, valid `LocalizationStrings` (at least `en` key, non-empty) |
| `description` | Required, valid `LocalizationStrings` (at least `en` key, non-empty) |
| `priority` | Required, > 0 |
| `softWarningPercent` | 1–100 |
| `dailyTokenLimit` | null or > 0 |
| `weeklyTokenLimit` | null or > 0 |
| `monthlyTokenLimit` | null or > 0 |
| `requestsPerMinute` | null or > 0 |
| `assignedUserGroupId` | null, or must exist AND must not be assigned to another tier |

---

## Error Messages

| Key | English | German |
|-----|---------|--------|
| `BudgetTier_NotFound` | Budget tier not found. | Budget-Stufe nicht gefunden. |
| `BudgetTier_CannotDeleteDefault` | Cannot delete the default budget tier. Assign a different default first. | Die Standard-Budget-Stufe kann nicht gelöscht werden. Weisen Sie zuerst eine andere Standard-Stufe zu. |
| `BudgetTier_UserGroupAlreadyAssigned` | This user group is already assigned to another budget tier. | Diese Benutzergruppe ist bereits einer anderen Budget-Stufe zugeordnet. |
| `BudgetTier_UserGroupNotFound` | The specified user group does not exist. | Die angegebene Benutzergruppe existiert nicht. |

---

## Not Yet Available

- **Rate Limiting** (`requestsPerMinute`): field exists and is persisted, but enforcement is not yet implemented. The UI can show the field but should mark it as "coming soon" or similar.
- **Cost Display**: no USD/EUR cost fields — costs are estimated from token usage with a fixed factor (frontend-side calculation if needed).
