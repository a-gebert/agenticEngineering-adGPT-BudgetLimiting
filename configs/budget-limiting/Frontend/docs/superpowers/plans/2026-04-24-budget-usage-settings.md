# Budget Usage Settings Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/settings/budget` page showing per-user token consumption as progress bars with color-coded thresholds.

**Architecture:** New `BudgetSettingsStore` (signalStore) calls `GET /api/budget/overview`, provided at shell level for sidebar visibility gating. `BudgetSettingsComponent` renders the data in a single section with Tailwind-styled progress bars.

**Tech Stack:** Angular 21, @ngrx/signals, Tailwind CSS 4, Transloco i18n, @hey-api/openapi-ts generated API client

**Spec:** `configs/budget-limiting/Frontend/docs/superpowers/specs/2026-04-24-budget-usage-settings-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `libs/chat/src/features/settings/budget-settings/budget-settings.store.ts` | Signal store: loads overview, exposes `isBudgetEnabled`, `periods`, `tierName`, `renewalDate` |
| `libs/chat/src/features/settings/budget-settings/budget-settings.component.ts` | Standalone component: injects store, renders template |
| `libs/chat/src/features/settings/budget-settings/budget-settings.component.html` | Template: progress bars, tier badge, disabled exception button |

### Modified Files

| File | Change |
|------|--------|
| `libs/chat/src/lib.routes.ts` | Add `budget` child route under `settings` |
| `libs/chat/src/features/settings/settings-shell.component.ts` | Inject `BudgetSettingsStore`, add to providers |
| `libs/chat/src/features/settings/settings-shell.component.html` | Add conditional `<cd-navigation-item>` for budget |
| `libs/chat/src/i18n/chat/de.json` | Add `pages.settings.budget.*` keys |
| `libs/chat/src/i18n/chat/en.json` | Add `pages.settings.budget.*` keys |
| `libs/chat/src/i18n/chat/fr.json` | Add `pages.settings.budget.*` keys |

---

### Task 1: Regenerate API Client

**Files:**
- Modify: `libs/api/src/generated/types.gen.ts` (auto-generated)
- Modify: `libs/api/src/generated/sdk.gen.ts` (auto-generated)

- [ ] **Step 1: Start the backend**

Run from a separate terminal:

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Backend/Presentation/adessoGPT.Presentation.Api
dotnet run --launch-profile IntegrationTest
```

Wait for `Now listening on: http://localhost:5522`.

- [ ] **Step 2: Regenerate the API client**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run generate:api
```

- [ ] **Step 3: Verify budget types exist**

```bash
grep -n "BudgetOverview\|BudgetPeriodSummary\|BudgetState" libs/api/src/generated/types.gen.ts
```

Expected: types for `GetBudgetOverviewQueryResponse`, `BudgetPeriodSummary` are present.

- [ ] **Step 4: Verify budget API service exists**

```bash
grep -n "budget" libs/api/src/generated/sdk.gen.ts
```

Expected: a generated service class with methods for `GET /api/budget/overview` and `GET /api/budget/state`.

- [ ] **Step 5: Kill the backend process**

- [ ] **Step 6: Commit**

```bash
git add libs/api/src/generated/
git commit -m "chore: regenerate API client with budget endpoints"
```

**Fallback if backend cannot be started:** Skip this task and use a temporary manual API call in the store (see Task 2 fallback section). Return to this task later.

---

### Task 2: Create BudgetSettingsStore

**Files:**
- Create: `libs/chat/src/features/settings/budget-settings/budget-settings.store.ts`

- [ ] **Step 1: Create the store file**

```typescript
import { NotificationService } from '@adesso-gpt/corporate-design';
import { computed, inject } from '@angular/core';
import { patchState, signalStore, withComputed, withHooks, withMethods, withProps, withState } from '@ngrx/signals';

type BudgetPeriodDisplay = {
  key: 'daily' | 'weekly' | 'monthly';
  tokensUsed: number;
  tokenLimit: number | null;
  usagePercent: number | null;
  periodEnd: string;
};

type BudgetSettingsState = {
  overview: {
    isEnabled: boolean;
    monthlyTokenLimit: number | null;
    daily: { periodStart: string; periodEnd: string; tokensUsed: number; costUsd: number; requestCount: number; lastRecordedAt: string | null } | null;
    weekly: { periodStart: string; periodEnd: string; tokensUsed: number; costUsd: number; requestCount: number; lastRecordedAt: string | null } | null;
    monthly: { periodStart: string; periodEnd: string; tokensUsed: number; costUsd: number; requestCount: number; lastRecordedAt: string | null } | null;
  } | null;
  isLoading: boolean;
};

const initialState: BudgetSettingsState = {
  overview: null,
  isLoading: true,
};

export const BudgetSettingsStore = signalStore(
  withState(initialState),

  withProps(() => ({
    _budgetApi: inject(BudgetApiService),
    _notificationService: inject(NotificationService),
  })),

  withComputed((store) => ({
    isBudgetEnabled: computed(() => store.overview()?.isEnabled ?? false),
    tierName: computed(() => 'Standard'),
  })),

  withComputed((store) => ({
    periods: computed(() => {
      const overview = store.overview();

      if (!overview) {
        return [];
      }

      const limit = overview.monthlyTokenLimit;
      const result: BudgetPeriodDisplay[] = [];

      if (overview.daily) {
        result.push({
          key: 'daily',
          tokensUsed: overview.daily.tokensUsed,
          tokenLimit: null,
          usagePercent: null,
          periodEnd: overview.daily.periodEnd,
        });
      }

      if (overview.weekly) {
        result.push({
          key: 'weekly',
          tokensUsed: overview.weekly.tokensUsed,
          tokenLimit: null,
          usagePercent: null,
          periodEnd: overview.weekly.periodEnd,
        });
      }

      if (overview.monthly) {
        const usagePercent = limit ? Math.min(Math.round((overview.monthly.tokensUsed / limit) * 100), 100) : null;
        result.push({
          key: 'monthly',
          tokensUsed: overview.monthly.tokensUsed,
          tokenLimit: limit,
          usagePercent,
          periodEnd: overview.monthly.periodEnd,
        });
      }

      return result;
    }),

    renewalDate: computed(() => {
      const overview = store.overview();

      if (!overview) {
        return null;
      }

      const longestPeriod = overview.monthly ?? overview.weekly ?? overview.daily;
      return longestPeriod?.periodEnd ?? null;
    }),
  })),

  withMethods((store) => ({
    async loadOverview(): Promise<void> {
      patchState(store, { isLoading: true });

      try {
        const response = await store._budgetApi.getBudgetOverview();
        patchState(store, { overview: response.data ?? null, isLoading: false });
      } catch (error) {
        patchState(store, { isLoading: false });
        store._notificationService.unknownErrorWithFallback(error, {
          code: 'BUDGET_OVERVIEW_LOAD_FAILED',
          message: 'Failed to load budget overview.',
        });
      }
    },
  })),

  withHooks({
    onInit(store) {
      store.loadOverview();
    },
  }),
);
```

**Important:** The `BudgetApiService` import depends on Task 1. If the API client was regenerated, find the exact generated service name:

```bash
grep -n "class.*Api.*budget" libs/api/src/generated/sdk.gen.ts
```

And replace `BudgetApiService` with the actual class name and add the correct import from `@adesso-gpt/api`.

**Fallback (if API client not regenerated):** Use the raw client temporarily:

```typescript
import { client } from '@adesso-gpt/api';

// In withProps:
_budgetApi: null as never, // placeholder

// In withMethods, replace the API call:
const response = await client.get({ url: '/api/budget/overview' });
patchState(store, { overview: response.data ?? null, isLoading: false });
```

- [ ] **Step 2: Verify the file compiles**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run build
```

Fix any import or type errors.

- [ ] **Step 3: Commit**

```bash
git add libs/chat/src/features/settings/budget-settings/budget-settings.store.ts
git commit -m "feat: add BudgetSettingsStore for budget overview"
```

---

### Task 3: Create BudgetSettingsComponent

**Files:**
- Create: `libs/chat/src/features/settings/budget-settings/budget-settings.component.ts`
- Create: `libs/chat/src/features/settings/budget-settings/budget-settings.component.html`

- [ ] **Step 1: Create the component TypeScript file**

```typescript
import {
  ButtonComponent,
  ChipComponent,
  ContentPageComponent,
  IconComponent,
  SeparatorComponent,
  SpinnerComponent,
} from '@adesso-gpt/corporate-design';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { BudgetSettingsStore } from './budget-settings.store';

@Component({
  selector: 'chat-budget-settings',
  standalone: true,
  imports: [
    ContentPageComponent,
    IconComponent,
    ChipComponent,
    SpinnerComponent,
    SeparatorComponent,
    ButtonComponent,
    TranslocoPipe,
  ],
  templateUrl: './budget-settings.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BudgetSettingsComponent {
  readonly store = inject(BudgetSettingsStore);
}
```

- [ ] **Step 2: Create the component HTML template**

```html
<cd-content-page container>
  <div class="flex max-w-xl flex-col gap-4">
    @if (store.isLoading()) {
      <div class="flex items-center justify-center py-12">
        <cd-spinner size="lg" />
      </div>
    } @else {
      <section class="border-separator rounded border p-4">
        <!-- Header -->
        <div class="mb-4 flex items-center gap-2">
          <cd-icon icon="mgc_chart_bar_line" size="sm" />
          <span class="text-sm font-semibold">{{ 'chat.pages.settings.budget.title' | transloco }}</span>
          <div class="ml-auto">
            <cd-chip [text]="store.tierName()" variant="success" />
          </div>
        </div>

        <!-- Period bars -->
        @for (period of store.periods(); track period.key) {
          <div class="mb-3">
            <div class="mb-1 flex items-center justify-between">
              <span class="text-muted text-xs">
                {{ 'chat.pages.settings.budget.period' + period.key.charAt(0).toUpperCase() + period.key.slice(1) | transloco }}
              </span>
              @if (period.tokenLimit !== null) {
                <span
                  class="text-xs font-medium"
                  [class.text-warning]="period.usagePercent !== null && period.usagePercent >= 80 && period.usagePercent < 100"
                  [class.text-error]="period.usagePercent !== null && period.usagePercent >= 100"
                >
                  {{ period.tokensUsed | number }} / {{ period.tokenLimit | number }}
                </span>
              } @else {
                <span class="text-xs font-medium">
                  {{ period.tokensUsed | number }} Tokens
                </span>
              }
            </div>

            @if (period.tokenLimit !== null && period.usagePercent !== null) {
              <div class="h-2 overflow-hidden rounded-full bg-ramp-surface-200">
                <div
                  class="h-full rounded-full transition-all"
                  [class.bg-ramp-primary-500]="period.usagePercent < 80"
                  [class.bg-ramp-warning-500]="period.usagePercent >= 80 && period.usagePercent < 100"
                  [class.bg-ramp-error-500]="period.usagePercent >= 100"
                  [style.width.%]="period.usagePercent"
                ></div>
              </div>
            }
          </div>
        }

        <!-- Footer -->
        <cd-separator />
        <div class="mt-3 flex items-center justify-between">
          @if (store.renewalDate(); as renewalDate) {
            <span class="text-muted text-xs">
              {{ 'chat.pages.settings.budget.renewalDate' | transloco: { date: (renewalDate | date: 'mediumDate') } }}
            </span>
          }
          <cd-button
            variant="card"
            size="sm"
            ariaLabel="{{ 'chat.pages.settings.budget.requestException' | transloco }}"
            [disabled]="true"
            [tooltip]="'chat.pages.settings.budget.comingSoon' | transloco"
            [clickCallback]="undefined"
          >
            {{ 'chat.pages.settings.budget.requestException' | transloco }}
          </cd-button>
        </div>
      </section>
    }
  </div>
</cd-content-page>
```

**Note on the `number` pipe:** Import `DecimalPipe` from `@angular/common` and add it to the component's `imports` array. Same for `DatePipe`.

Updated component imports:

```typescript
import { DatePipe, DecimalPipe } from '@angular/common';
// ... add to imports array:
imports: [
  ContentPageComponent,
  IconComponent,
  ChipComponent,
  SpinnerComponent,
  SeparatorComponent,
  ButtonComponent,
  TranslocoPipe,
  DecimalPipe,
  DatePipe,
],
```

- [ ] **Step 3: Verify the file compiles**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run build
```

Fix any template or import errors.

- [ ] **Step 4: Commit**

```bash
git add libs/chat/src/features/settings/budget-settings/
git commit -m "feat: add BudgetSettingsComponent with progress bars"
```

---

### Task 4: Wire Routing, Sidebar, and Provider

**Files:**
- Modify: `libs/chat/src/lib.routes.ts`
- Modify: `libs/chat/src/features/settings/settings-shell.component.ts`
- Modify: `libs/chat/src/features/settings/settings-shell.component.html`

- [ ] **Step 1: Add the budget route**

In `libs/chat/src/lib.routes.ts`, add inside the `settings` children array, after the `shared-links` route:

```typescript
{
  path: 'budget',
  component: BudgetSettingsComponent,
  title: 'chat.pages.settings.budget.sidebarLabel',
},
```

Add the import at the top:

```typescript
import { BudgetSettingsComponent } from './features/settings/budget-settings/budget-settings.component';
```

- [ ] **Step 2: Provide BudgetSettingsStore at settings shell level**

In `libs/chat/src/features/settings/settings-shell.component.ts`:

Add import:

```typescript
import { BudgetSettingsStore } from './budget-settings/budget-settings.store';
```

Add `providers` to the `@Component` decorator:

```typescript
@Component({
  // ... existing config
  providers: [BudgetSettingsStore],
})
```

Inject the store in the class:

```typescript
export class SettingsShellComponent {
  readonly store = inject(LayoutStore);
  readonly budgetSettingsStore = inject(BudgetSettingsStore);
}
```

- [ ] **Step 3: Add conditional sidebar item**

In `libs/chat/src/features/settings/settings-shell.component.html`, add before `<router-outlet />` (after the last `<cd-navigation-item>`):

```html
@if (budgetSettingsStore.isBudgetEnabled()) {
  <cd-navigation-item
    ariaLabel="{{ 'chat.pages.settings.budget.sidebarLabel' | transloco }}"
    text="{{ 'chat.pages.settings.budget.sidebarLabel' | transloco }}"
    icon="mgc_chart_bar_line"
    routerLink="./budget"
  />
}
```

- [ ] **Step 4: Verify build**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add libs/chat/src/lib.routes.ts libs/chat/src/features/settings/settings-shell.component.ts libs/chat/src/features/settings/settings-shell.component.html
git commit -m "feat: wire budget settings route, sidebar, and store provider"
```

---

### Task 5: Add i18n Translation Keys

**Files:**
- Modify: `libs/chat/src/i18n/chat/de.json`
- Modify: `libs/chat/src/i18n/chat/en.json`
- Modify: `libs/chat/src/i18n/chat/fr.json`

- [ ] **Step 1: Add German translations**

In `libs/chat/src/i18n/chat/de.json`, add inside `pages.settings` (after the `language` block):

```json
"budget": {
  "title": "Token-Verbrauch",
  "sidebarLabel": "Budget",
  "periodDaily": "Heute",
  "periodWeekly": "Diese Woche",
  "periodMonthly": "Dieser Monat",
  "renewalDate": "Erneuert am {{date}}",
  "requestException": "Budget-Ausnahme anfragen",
  "comingSoon": "Demnächst verfügbar"
}
```

- [ ] **Step 2: Add English translations**

In `libs/chat/src/i18n/chat/en.json`, add inside `pages.settings`:

```json
"budget": {
  "title": "Token Usage",
  "sidebarLabel": "Budget",
  "periodDaily": "Today",
  "periodWeekly": "This Week",
  "periodMonthly": "This Month",
  "renewalDate": "Renews on {{date}}",
  "requestException": "Request Budget Exception",
  "comingSoon": "Coming soon"
}
```

- [ ] **Step 3: Add French translations**

In `libs/chat/src/i18n/chat/fr.json`, add inside `pages.settings`:

```json
"budget": {
  "title": "Utilisation des tokens",
  "sidebarLabel": "Budget",
  "periodDaily": "Aujourd'hui",
  "periodWeekly": "Cette semaine",
  "periodMonthly": "Ce mois-ci",
  "renewalDate": "Renouvellement le {{date}}",
  "requestException": "Demander une exception",
  "comingSoon": "Bientôt disponible"
}
```

- [ ] **Step 4: Verify JSON validity**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
python3 -c "import json; json.load(open('libs/chat/src/i18n/chat/de.json'))"
python3 -c "import json; json.load(open('libs/chat/src/i18n/chat/en.json'))"
python3 -c "import json; json.load(open('libs/chat/src/i18n/chat/fr.json'))"
```

- [ ] **Step 5: Commit**

```bash
git add libs/chat/src/i18n/chat/
git commit -m "feat: add budget settings i18n keys (de, en, fr)"
```

---

### Task 6: Fix Template Translation Keys

The template in Task 3 uses a dynamic Transloco key via string concatenation (`'chat.pages.settings.budget.period' + period.key...`). This pattern does not work with Transloco's static analysis. Fix by using an explicit key map in the component.

**Files:**
- Modify: `libs/chat/src/features/settings/budget-settings/budget-settings.component.ts`
- Modify: `libs/chat/src/features/settings/budget-settings/budget-settings.component.html`

- [ ] **Step 1: Add a period label map to the component**

In `budget-settings.component.ts`, add a readonly property:

```typescript
export class BudgetSettingsComponent {
  readonly store = inject(BudgetSettingsStore);

  readonly periodLabels: Record<string, string> = {
    daily: 'chat.pages.settings.budget.periodDaily',
    weekly: 'chat.pages.settings.budget.periodWeekly',
    monthly: 'chat.pages.settings.budget.periodMonthly',
  };
}
```

- [ ] **Step 2: Update the template to use the map**

Replace the dynamic transloco key in `budget-settings.component.html`:

```html
<!-- Replace this: -->
{{ 'chat.pages.settings.budget.period' + period.key.charAt(0).toUpperCase() + period.key.slice(1) | transloco }}

<!-- With this: -->
{{ periodLabels[period.key] | transloco }}
```

- [ ] **Step 3: Build and verify**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run build
```

- [ ] **Step 4: Commit**

```bash
git add libs/chat/src/features/settings/budget-settings/
git commit -m "fix: use static transloco keys for budget period labels"
```

---

### Task 7: Final Verification

- [ ] **Step 1: Full build**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Lint**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run lint
```

Fix any lint violations.

- [ ] **Step 3: Format**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run prettier
```

- [ ] **Step 4: Start dev server and test manually**

```bash
cd /home/gebert/adgpt/PBI3271_Budget_Limits/dev/app/Frontend/adessoGPT.Web
npm run dev
```

Navigate to `https://localhost:5174/settings/budget` and verify:
- Sidebar shows "Budget" entry (if backend returns `isEnabled: true`)
- Page shows progress bars for configured periods
- Monthly bar has color-coded fill
- Daily/weekly show absolute token count
- Tier badge shows "Standard"
- "Budget-Ausnahme anfragen" button is disabled with tooltip
- Renewal date is shown

- [ ] **Step 5: Commit formatting changes if any**

```bash
git add -A
git commit -m "style: format budget settings files"
```
