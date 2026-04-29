# Admin Budget Report — Implementierungsplan

## Context

Admins brauchen eine Ubersicht uber den Token-Verbrauch aller User im Control Center. Der Backend-Endpoint `GET /api/control-center/budget/report` existiert bereits (paginiert, Period/Date-Filter). Die User-seitige Budget-Settings-Seite existiert ebenfalls als Referenz. Ziel: Prototyp mit Summary-Karten oben + Datentabelle unten.

**Design-Entscheidungen (vom User bestatigt):**
- Layout: Kombination (Summary + Tabelle)
- Projection: Lineare Extrapolation clientseitig
- Filter: Kein Gruppenfilter, nur Textsuche auf UserId
- Limit: Keine Limit-Anzeige (nur Verbrauch)

## Neue Dateien

### 1. `libs/control-center/src/features/budget-report/budget-report.store.ts`

SignalStore mit:
- **State**: `entries: BudgetUsageEntryDto[]`, `totalCount`, `pageNumber`, `pageSize`, `totalPages`, `selectedPeriod: 'Monthly' | null`, `searchQuery: string`
- **withLoading()** fur Loading/Error-State
- **withProps**: `_budgetAdminApi: inject(BudgetAdministrationApiService)`, `_translocoService: inject(TranslocoService)`
- **withComputed**:
  - `filteredEntries` — clientseitiger Filter auf `searchQuery` (userId enthalt Suchtext)
  - `summary` — computed mit `totalUsers` (unique userIds), `totalTokensUsed`, `totalCostUsd`, `totalRequests` (jeweils Summe uber alle Entries)
  - `entriesWithProjection` — mapt jede Entry auf ein erweitertes Objekt mit `projectedTokens: number | null`. Berechnung fur monatliche Eintrags: `(tokensUsed / elapsedDays) * totalDaysInPeriod`. Fur andere Perioden: `null`.
- **withMethods**: `loadReport()` — ruft `getBudgetUsageReport({ query: { Period: selectedPeriod, PageNumber: 1, PageSize: 500 } })` auf
- **withMethods**: `setSearchQuery(query)`, `setPeriod(period)`
- **withHooks**: `onInit` -> `loadReport()`

### 2. `libs/control-center/src/features/budget-report/budget-report.component.ts`

- Standalone, OnPush, `providers: [BudgetReportStore]`
- `store = inject(BudgetReportStore)`
- Search-Input Binding uber `[(value)]` auf store.setSearchQuery
- Period-Select uber `forms-select` mit Optionen Monthly/Weekly/Daily/All

### 3. `libs/control-center/src/features/budget-report/budget-report.component.html`

Layout:
```
<cd-content-page [loading]="..." [loadingError]="...">
  <!-- Filter bar -->
  <div> Period-Select + Suchfeld </div>

  <!-- Summary cards -->
  <div class="grid grid-cols-4 gap-4">
    <card> Total Users </card>
    <card> Total Tokens </card>
    <card> Total Cost </card>
    <card> Total Requests </card>
  </div>

  <!-- Data table -->
  <table>
    <thead> User ID | Tokens Used | Projected | Cost | Requests | Last Active </thead>
    <tbody> @for entry of entriesWithProjection </tbody>
  </table>
</cd-content-page>
```

Summary-Karten: `surface-card` mit `cd-icon` + Zahl. Tailwind Grid 4 Spalten (responsive: 2 auf mobil).

Tabelle: Einfache HTML-Tabelle mit Tailwind-Klassen. Projected-Spalte zeigt einen Pfeil-Indikator wenn Projection > aktueller Verbrauch.

## Geanderte Dateien

### 4. `libs/control-center/src/lib.routes.ts`

Import hinzufugen:
```typescript
import { BudgetReportComponent } from './features/budget-report/budget-report.component';
```

Route hinzufugen (nach `administration` Block, ca. Zeile 84):
```typescript
{
  path: 'budget-report',
  component: BudgetReportComponent,
  title: 'control-center.navigation.budget-report',
},
```

### 5. `libs/control-center/src/shell/navigation/navigation.component.html`

Neuer Nav-Item unter Administration (nach Zeile 127, vor `</cd-navigation-item-group>`):
```html
<cd-navigation-item
  ariaLabel="{{ 'control-center.navigation.budget-report' | transloco }}"
  text="{{ 'control-center.navigation.budget-report' | transloco }}"
  icon="mgc_chart_bar_line"
  routerLink="./budget-report"
/>
```

### 6. i18n — alle 4 Sprachdateien

**Navigation-Key** (in `navigation` Objekt):
```json
"budget-report": "Budget Report"
```

**Feature-Keys** (neues Top-Level-Objekt `budgetReport`):
```json
"budgetReport": {
  "page-description": "Overview of token usage across all users",
  "summary-total-users": "Users",
  "summary-total-tokens": "Total Tokens",
  "summary-total-cost": "Total Cost",
  "summary-total-requests": "Total Requests",
  "table-header-user": "User ID",
  "table-header-tokens": "Tokens Used",
  "table-header-projected": "Projected",
  "table-header-cost": "Cost (USD)",
  "table-header-requests": "Requests",
  "table-header-last-active": "Last Active",
  "search-placeholder": "Search by user ID...",
  "period-all": "All Periods",
  "period-monthly": "Monthly",
  "period-weekly": "Weekly",
  "period-daily": "Daily",
  "empty": "No budget usage data available.",
  "errors": {
    "load-failed": "Failed to load budget report.",
    "load-failedSolution": "Please try again later."
  }
}
```

Deutsche, franzosische, italienische Ubersetzungen analog.

## Projection-Logik (clientseitig)

```typescript
function calculateProjection(entry: BudgetUsageEntryDto): number | null {
  if (entry.period !== 'monthly') return null;
  
  const periodStart = new Date(entry.periodStart);
  const periodEnd = new Date(entry.periodEnd);
  const now = new Date();
  
  const totalDays = (periodEnd.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24);
  const elapsedDays = (now.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24);
  
  if (elapsedDays <= 0 || totalDays <= 0) return entry.tokensUsed;
  
  return Math.round((entry.tokensUsed / elapsedDays) * totalDays);
}
```

## Dateien-Ubersicht

| Datei | Aktion |
|-------|--------|
| `features/budget-report/budget-report.store.ts` | NEU |
| `features/budget-report/budget-report.component.ts` | NEU |
| `features/budget-report/budget-report.component.html` | NEU |
| `lib.routes.ts` | EDIT — Import + Route |
| `shell/navigation/navigation.component.html` | EDIT — Nav-Item |
| `i18n/control-center/en.json` | EDIT — nav key + feature keys |
| `i18n/control-center/de.json` | EDIT — nav key + feature keys |
| `i18n/control-center/fr.json` | EDIT — nav key + feature keys |
| `i18n/control-center/it.json` | EDIT — nav key + feature keys |

## Referenz-Patterns (wiederverwendet)

- **FaqsStore** (`features/faqs/faqs.store.ts`) — withLoading + API-Call Pattern
- **FaqsComponent** (`features/faqs/faqs.component.ts`) — cd-content-page Wrapper
- **BudgetSettingsStore** (`chat/features/settings/budget-settings/budget-settings.store.ts`) — Budget-API Zugriffsmuster
- **BudgetAdministrationApiService** (`api/src/generated/sdk.gen.ts:776`) — generierter Admin-Endpoint

## Verifikation

1. `npm run build` — muss ohne Fehler durchlaufen
2. Dev-Server starten (`npm run dev`) und `/control-center/budget-report` aufrufen
3. Pruefen: Navigation-Eintrag unter "Administration" sichtbar
4. Pruefen: Summary-Karten zeigen aggregierte Zahlen
5. Pruefen: Tabelle zeigt Eintrags mit Projection fur monatliche Daten
6. Pruefen: Suchfeld filtert nach User ID
7. Pruefen: Period-Filter ladt Daten neu
