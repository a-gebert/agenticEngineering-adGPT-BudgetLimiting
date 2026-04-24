# Budget Usage Settings Page — Design Spec

**Date:** 2026-04-24
**Feature:** PBI3271 Budget Limits
**Branch:** feature/PBI3271_Budget_Limits
**Scope:** New settings page showing per-user token budget usage with progress bars

---

## Overview

Add a "Budget" entry to the user settings sidebar at `/settings/budget`. The page displays the user's current token consumption across all configured periods (daily, weekly, monthly) as progress bars with color-coded thresholds. A disabled "Request budget exception" button prepares the UI for a future admin-request feature.

The sidebar entry is only visible when the budget feature is enabled in the backend (`isEnabled: true` from `GET /api/budget/overview`).

---

## API Dependency

**Endpoint:** `GET /api/budget/overview`
**Source:** `Backend/Application/adessoGPT.Application/Business/Budget/BudgetEndpoints.cs`

**Response shape (`GetBudgetOverviewQueryResponse`):**
```json
{
  "isEnabled": true,
  "monthlyTokenLimit": 500000,
  "daily": {
    "periodStart": "2026-04-24T00:00:00Z",
    "periodEnd": "2026-04-25T00:00:00Z",
    "tokensUsed": 4200,
    "costUsd": 0.42,
    "requestCount": 12,
    "lastRecordedAt": "2026-04-24T10:30:00Z"
  },
  "weekly": { ... },
  "monthly": { ... }
}
```

Periods not configured by the admin are `null` in the response and will not be rendered.

**Prerequisite:** Run `npm run generate:api` to generate the typed API client for this endpoint before implementation.

---

## Routing & Sidebar

- New child route `budget` under the `settings` parent in `libs/chat/src/lib.routes.ts`
- Lazy-loaded `BudgetSettingsComponent`
- New `<cd-navigation-item>` in `settings-shell.component.html` with icon and label "Budget"
- The sidebar entry is conditionally rendered: only shown when `isBudgetEnabled()` signal is `true`
- The `BudgetSettingsStore` is provided at the `SettingsShellComponent` level so the `isBudgetEnabled` signal is available for sidebar visibility and the data is shared with the budget page

---

## Component: BudgetSettingsComponent

**Location:** `libs/chat/src/features/settings/budget-settings/`
**Files:** `budget-settings.component.ts`, `budget-settings.component.html`

### Layout

- Wrapped in `<cd-content-page container>` with `max-w-xl` constraint (consistent with other settings pages)
- Single section with `border-separator rounded border p-4`

### Structure

```
┌─────────────────────────────────────────────┐
│ [icon]  Token-Verbrauch          [Standard] │  ← Tier badge as chip
│                                             │
│ Heute                           4.200       │  ← absolute only, no limit
│                                             │
│ Diese Woche                    38.750       │  ← absolute only, no limit
│                                             │
│ Dieser Monat     125.432 / 500.000          │
│ [███████░░░░░░░░░░░░░░░░░░░░░]  25%        │  ← progress bar with color
│                                             │
│─────────────────────────────────────────────│
│ Erneuert am 01.05.2026    [Ausnahme anfr.] │  ← button disabled
└─────────────────────────────────────────────┘
```

### Display Logic Per Period

The backend currently only provides `monthlyTokenLimit` — there are no per-period limits for daily/weekly.

- **Monthly (has limit):** Progress bar with percentage, color-coded. Shows "125.432 / 500.000".
- **Daily / Weekly (no limit):** Absolute token count only, no progress bar. Shows "4.200 Tokens".
- If `monthlyTokenLimit` is `null`, the monthly period also shows absolute count only (no bar).

### Progress Bar Color Logic (monthly bar only)

| Usage Percent | Bar Color | Text Accent |
|---|---|---|
| 0–79% | Blue (`primary` theme color) | Default |
| 80–99% | Yellow/amber (`warning` theme color) | Warning color |
| 100% | Red (`error` theme color) | Error color |

### Period Labels (i18n)

| Period | German | English | French |
|---|---|---|---|
| Daily | Heute | Today | Aujourd'hui |
| Weekly | Diese Woche | This Week | Cette semaine |
| Monthly | Dieser Monat | This Month | Ce mois-ci |

### Footer

- Left: renewal date — "Erneuert am {periodEnd}" of the longest active period (monthly > weekly > daily)
- Right: "Budget-Ausnahme anfragen" button — `disabled`, with tooltip "Demnächst verfügbar" / "Coming soon"

### Loading State

- While `isLoading()` is true: `<cd-spinner size="lg" />` centered
- Error state: `NotificationService.unknownErrorWithFallback()`

---

## Store: BudgetSettingsStore

**Location:** `libs/chat/src/features/settings/budget-settings/budget-settings.store.ts`

### State

```typescript
type BudgetSettingsState = {
  overview: GetBudgetOverviewQueryResponse | null;
  isLoading: boolean;
};

const initialState: BudgetSettingsState = {
  overview: null,
  isLoading: true,
};
```

### Structure (mandatory ordering)

1. `withState(initialState)`
2. `withProps()` — inject API service, `NotificationService`
3. `withComputed()`:
   - `isBudgetEnabled()` — `overview()?.isEnabled ?? false`
   - `tierName()` — derived from overview (initially hardcoded to tier name from response, future: separate tier endpoint)
   - `periods()` — array of `{ key: 'daily'|'weekly'|'monthly', tokensUsed: number, tokenLimit: number | null, usagePercent: number | null, periodEnd: DateTimeOffset }` filtered to non-null periods from overview. Only the monthly period gets `tokenLimit` and `usagePercent` (from `monthlyTokenLimit`). Daily/weekly have `tokenLimit: null` and `usagePercent: null`.
   - `renewalDate()` — `periodEnd` of the longest active period (monthly > weekly > daily)
4. `withMethods()`:
   - `loadOverview()` — `GET /api/budget/overview`, patchState, error handling
5. `withHooks()`:
   - `onInit` → `loadOverview()`

### Provider Scope

Provided at `SettingsShellComponent` level (`providers: [BudgetSettingsStore]`) so:
- Sidebar can read `isBudgetEnabled()` for conditional rendering
- `BudgetSettingsComponent` uses the same store instance

---

## i18n Keys

Under scope `chat`, keys at `chat.pages.settings.budget.*`:

```
budget.title              → "Token-Verbrauch" / "Token Usage" / "Utilisation des tokens"
budget.tierLabel          → (no label, just the tier name as badge)
budget.periodDaily        → "Heute" / "Today" / "Aujourd'hui"
budget.periodWeekly       → "Diese Woche" / "This Week" / "Cette semaine"
budget.periodMonthly      → "Dieser Monat" / "This Month" / "Ce mois-ci"
budget.renewalDate        → "Erneuert am {{date}}" / "Renews on {{date}}" / "Renouvellement le {{date}}"
budget.requestException   → "Budget-Ausnahme anfragen" / "Request Budget Exception" / "Demander une exception"
budget.comingSoon         → "Demnächst verfügbar" / "Coming soon" / "Bientôt disponible"
budget.sidebarLabel       → "Budget" / "Budget" / "Budget"
```

---

## Sidebar Navigation Item

```html
@if (budgetSettingsStore.isBudgetEnabled()) {
  <cd-navigation-item
    routerLink="budget"
    icon="bar_chart"
    [text]="'chat.pages.settings.budget.sidebarLabel' | transloco"
    [ariaLabel]="'chat.pages.settings.budget.sidebarLabel' | transloco"
  />
}
```

---

## Files to Create/Modify

### New Files
- `libs/chat/src/features/settings/budget-settings/budget-settings.component.ts`
- `libs/chat/src/features/settings/budget-settings/budget-settings.component.html`
- `libs/chat/src/features/settings/budget-settings/budget-settings.store.ts`

### Modified Files
- `libs/chat/src/lib.routes.ts` — add `budget` route
- `libs/chat/src/features/settings/settings-shell.component.ts` — inject `BudgetSettingsStore`, add to providers
- `libs/chat/src/features/settings/settings-shell.component.html` — add conditional sidebar item
- `libs/chat/src/i18n/chat/de.json` — add budget keys
- `libs/chat/src/i18n/chat/en.json` — add budget keys
- `libs/chat/src/i18n/chat/fr.json` — add budget keys

### Prerequisite
- Run `npm run generate:api` to generate typed API client for `GET /api/budget/overview`

---

## Out of Scope

- Budget exception request functionality (button is disabled placeholder)
- Request count display (only token usage shown)
- Cost/USD display
- Chat-stream warning/exhausted banner integration (separate feature)
- Admin-side budget configuration UI
