# Plan: BudgetTier CRUD im ControlCenter

## Context

Die provisorische `budget-settings`-Seite zeigt nur eine read-only Overview (Budget aktiv/inaktiv, monatliches Limit). Das Backend hat jetzt vollständige CRUD-Endpoints für **BudgetTiers** (Budget-Stufen): List, Get, Create, Update, Delete, Set-Default. Die API ist noch nicht im generierten Client — Workaround über manuellen API-Service mit `apiClient`.

**Ziel:** Provisorische `budget-settings` durch vollständige BudgetTier-Verwaltung ersetzen (List + Upsert). `budget-report` bleibt unverändert.

---

## 1. Temporären BudgetTier API Service erstellen

**Neu:** `features/budget-tiers/budget-tier-api.service.ts`

Manuell getypte Interfaces (werden nach API-Regenerierung durch generierte Typen ersetzt):

```typescript
// Typen direkt im Service-File
interface BudgetTierDto {
  title: Record<string, string>;
  description: Record<string, string>;
  priority: number;
  assignedUserGroupId?: string | null;
  dailyTokenLimit?: number | null;
  weeklyTokenLimit?: number | null;
  monthlyTokenLimit?: number | null;
  requestsPerMinute?: number | null;
  softWarningPercent: number;
}

interface BudgetTierItem extends BudgetTierDto {
  id: string;
  isDefault: boolean;
  assignedUserGroupTitle?: string | null;
}
```

Methoden via `apiClient.get/post/put/delete` gegen `/api/control-center/budget-tiers`.

## 2. List-Komponente: `budget-tiers/`

**Neu:** 3 Dateien nach user-groups-Muster

- `budget-tiers.component.ts` — SelectionPage mit Create-Button
- `budget-tiers.component.html` — `ccc-selection-page` mit Tier-Cards, `cd-chip` für Default/Priority/Limits
- `budget-tiers.store.ts` — `signalStore` mit `withLoading`, lädt Tiers im `onInit`

**Card-Darstellung pro Tier:**
- Title + Description
- `cd-chip variant="primary"` für Priority
- `cd-chip variant="success"` für Default-Tier
- `cd-chip variant="info"` für zugewiesene Benutzergruppe
- Token-Limits als Info-Text (selectionItemBody)

## 3. Upsert-Komponente: `budget-tiers/upsert/`

**Neu:** 3 Dateien nach user-groups-Muster

- `budget-tiers-upsert.component.ts`
- `budget-tiers-upsert.component.html`
- `budget-tiers-upsert.store.ts`

**Form-Felder:**
| Feld | Control | Validierung |
|------|---------|-------------|
| title | `forms-localized-textbox` | required |
| description | `forms-localized-textarea` | — |
| priority | `forms-textbox type="number"` | required, min 1 |
| assignedUserGroupId | `forms-select` (UserGroups laden) | optional |
| dailyTokenLimit | `forms-textbox type="number"` | optional, min 1 |
| weeklyTokenLimit | `forms-textbox type="number"` | optional, min 1 |
| monthlyTokenLimit | `forms-textbox type="number"` | optional, min 1 |
| requestsPerMinute | `forms-textbox type="number"` (readonly, "coming soon" hint) | optional |
| softWarningPercent | `forms-textbox type="number"` | required, 1–100, default 80 |

**Aktionen:**
- Save (Create/Update)
- Delete (mit ConfirmService, blocked wenn default)
- "Als Standard festlegen" Button (nur im Edit-Mode, nicht wenn bereits default)

**UserGroup-Dropdown:** Lädt Gruppen via `ControlCenterUserGroupsApiService.getControlCenterUserGroups()`, mapped zu `SelectOption[]`.

## 4. Provisorische Dateien löschen

**Löschen:** `features/budget-settings/` (3 Dateien: component.ts, component.html, store.ts)

## 5. Routes aktualisieren

**Datei:** `lib.routes.ts`

```typescript
// ALT
{ path: 'budget-settings', component: BudgetSettingsComponent, title: '...' }

// NEU
{
  path: 'budget-tiers',
  children: [
    { path: '', component: BudgetTiersComponent, title: 'control-center.navigation.budget-tiers' },
    { path: 'create', component: BudgetTiersUpsertComponent, canDeactivate: [...], title: '...' },
    { path: ':budgetTierId', component: BudgetTiersUpsertComponent, canDeactivate: [...], title: '...' },
  ],
}
```

Imports: `BudgetSettingsComponent` entfernen, `BudgetTiersComponent` + `BudgetTiersUpsertComponent` hinzufügen.

## 6. Navigation aktualisieren

**Datei:** `navigation.component.html`

Reihenfolge ändern: Budget-Stufen als Hauptelement, Budget-Bericht als `lastIndent` darunter.

```html
<cd-navigation-item icon="mgc_shield_line" routerLink="./budget-tiers" ... />
<cd-navigation-item lastIndent icon="mgc_chart_bar_line" routerLink="./budget-report" ... />
```

## 7. i18n aktualisieren (alle 4 Sprachen)

**Dateien:** `de.json`, `en.json`, `fr.json`, `it.json`

- Navigation: `budget-settings` → `budget-tiers` Key + Label
- `budgetSettings`-Sektion komplett ersetzen durch `budgetTiers`-Sektion mit neuen Keys:
  - `list-description`, `list-create-button`, `list-search-placeholder`, `list-empty`
  - `upsert-create-title`, `upsert-edit-title`
  - `upsert-*-label` für alle Formfelder
  - `upsert-delete-title`, `upsert-delete-description`
  - `upsert-set-default-button`, `upsert-is-default`
  - `chip-default`, `chip-unlimited`, `chip-requests-coming-soon`
  - `errors.load-failed`, `errors.create-failed`, `errors.update-failed`, `errors.delete-failed`, `errors.set-default-failed`
  - `limit-daily`, `limit-weekly`, `limit-monthly`, `unlimited`

## 8. Build prüfen

`npm run build` am Ende ausführen, um sicherzustellen dass alles kompiliert.

---

## Dateien-Übersicht

| Aktion | Pfad |
|--------|------|
| NEU | `features/budget-tiers/budget-tier-api.service.ts` |
| NEU | `features/budget-tiers/budget-tiers.component.ts` |
| NEU | `features/budget-tiers/budget-tiers.component.html` |
| NEU | `features/budget-tiers/budget-tiers.store.ts` |
| NEU | `features/budget-tiers/upsert/budget-tiers-upsert.component.ts` |
| NEU | `features/budget-tiers/upsert/budget-tiers-upsert.component.html` |
| NEU | `features/budget-tiers/upsert/budget-tiers-upsert.store.ts` |
| LÖSCHEN | `features/budget-settings/` (3 Dateien) |
| ÄNDERN | `lib.routes.ts` |
| ÄNDERN | `shell/navigation/navigation.component.html` |
| ÄNDERN | `i18n/control-center/de.json` |
| ÄNDERN | `i18n/control-center/en.json` |
| ÄNDERN | `i18n/control-center/fr.json` |
| ÄNDERN | `i18n/control-center/it.json` |

## Referenz-Dateien (Muster folgen)

- `features/user-groups/` — List + Upsert Pattern
- `features/user-groups/upsert/` — FormGroup + ControlMap + save/delete/navigate
- `libs/api/src/index.ts:5` — `apiClient` Export

## Verifikation

1. `npm run build` — keine Compile-Errors
2. Dev-Server starten, CC öffnen → Budget-Stufen Seite lädt (API-Fehler erwartet ohne Backend)
3. Navigation zeigt korrekte Struktur: Budget-Stufen → Budget-Bericht
4. Create/Edit-Route navigiert korrekt
