# Budget Banner — Frontend Aufgabenbeschreibung

**Datum:** 2026-04-28
**Branch:** feature/PBI3271_Budget_Limits
**Quelle:** `docs/superpowers/specs/2026-04-28-budget-banner-design.md`
**Voraussetzung:** Backend-Änderungen sind gemerged und die OpenAPI-Spec wurde regeneriert (`npm run generate:api`). Vor Start prüfen: der generierte Typ `ChatBudgetStatusResponse` mit Discriminator `event: 'budget_status'` muss in `libs/api` vorhanden sein.

## Ziel

Wenn das Backend während eines Chat-Sends das SSE-Event `budget_status` schickt, soll dem User ein Banner mit dem aktuellen Budget-Status, dem höchsten Prozentwert über alle Perioden und (bei aktivem Fallback-Modell) dem Fallback-Modell-Titel angezeigt werden.

## Backend-Vertrag (zur Information)

Genau ein neues SSE-Event ersetzt `budget_warning` und `budget_exhausted`:

```ts
type ChatBudgetStatusResponse = {
  event: 'budget_status';
  severity: 'Approaching' | 'Warning' | 'Exhausted';
  percentage: number;          // gerundet, höchste % über alle Perioden
  period: 'Daily' | 'Weekly' | 'Monthly';
  fallbackModelTitle: string | null;  // nur bei severity === 'Warning' gesetzt
};
```

Severity-Bedeutung:
- **Approaching** — Soft-Warnschwelle (z.B. 80%) überschritten, Limit noch nicht erreicht. Chat funktioniert normal.
- **Warning** — Hartes Limit erreicht, Agent läuft jetzt über das Fallback-Modell. Chat funktioniert weiter, aber mit `fallbackModelTitle`.
- **Exhausted** — Hartes Limit erreicht, kein Fallback-Modell. Chat-Stream endet sofort nach diesem Event (Backend macht `yield break`).

Das Backend ist **stateless**: das Event feuert bei jedem Chat-Send, der die Schwelle übersteigt. Throttling/Dismiss ist Frontend-Aufgabe.

## Aufgaben

### 1. Dispatch-Cases ergänzen

Aktuell fallen `budget_warning` und `budget_exhausted` in den `default`-Branch — sie hatten nie einen UI-Effekt. Die alten Cases werden durch einen neuen ersetzt:

- `libs/chat/src/features/chat/existing-chat/chat-stream.store.ts` — neuer `case 'budget_status'`.
- `libs/chat/src/features/chat/realtime/realtime.store.ts` — gleicher Case.

Beide rufen den neuen `BudgetBannerStore.setStatus(...)` auf.

### 2. BudgetBannerStore (NgRx Signals)

Pfad: `libs/chat/src/features/budget-banner/budget-banner.store.ts`

```ts
type BudgetBannerStatus = {
  severity: 'Approaching' | 'Warning' | 'Exhausted';
  percentage: number;
  period: 'Daily' | 'Weekly' | 'Monthly';
  fallbackModelTitle: string | null;
};

// signalStore:
//   withState({
//     currentStatus: null as BudgetBannerStatus | null,
//     dismissedSeverities: new Set<Severity>(),
//   })
//   withMethods(store => ({
//     setStatus(status) {
//       if (store.dismissedSeverities().has(status.severity)) return;
//       patchState(store, { currentStatus: status });
//     },
//     dismiss() {
//       const current = store.currentStatus();
//       if (!current) return;
//       const next = new Set(store.dismissedSeverities());
//       next.add(current.severity);
//       patchState(store, { currentStatus: null, dismissedSeverities: next });
//     },
//   }))
```

Folge der projektweiten Store-Reihenfolge `withState → withProps → withComputed → withMethods → withHooks`. **Kein** Persist — Reload soll den Store zurücksetzen.

### 3. Banner-Komponente

Render-Punkt: App-Shell (oder Chat-Layout, je nachdem wo andere globale Banner hängen — orientiere dich an bestehenden Mustern, z.B. `AppAlerts` im React-Frontend als inhaltliche Referenz).

- Bindet auf `budgetBannerStore.currentStatus`.
- `null` → nichts rendern.
- Severity-Farbcodierung: `Approaching` und `Warning` als Warn-Farbe, `Exhausted` als Error-Farbe.
- Dismiss-Button ruft `budgetBannerStore.dismiss()`.

### 4. i18n

Neue Keys in `libs/chat/.../i18n/{en,de}.json` (oder im passenden Modul-Bereich, je nach Konvention):

| Key | Inhalt (DE) | Inhalt (EN) |
|---|---|---|
| `budgetBanner.approaching` | `{period} zu {percentage}% ausgeschöpft.` | `{period} usage is at {percentage}%.` |
| `budgetBanner.warning` | `{period} erreicht. Antworten laufen jetzt über das Fallback-Modell „{fallbackModelTitle}".` | `{period} reached. Responses now run on the fallback model "{fallbackModelTitle}".` |
| `budgetBanner.exhausted` | `{period} erreicht. Es sind keine weiteren Anfragen möglich.` | `{period} reached. No further requests possible.` |
| `budgetBanner.period.Daily` | `Tageslimit` | `Daily limit` |
| `budgetBanner.period.Weekly` | `Wochenlimit` | `Weekly limit` |
| `budgetBanner.period.Monthly` | `Monatslimit` | `Monthly limit` |
| `budgetBanner.dismiss` | `Schließen` | `Dismiss` |

Keys-Namen sind ein Vorschlag — gerne der projektweiten Konvention angleichen.

### 5. Tests

- Store-Test: nach `dismiss(Approaching)` setzt `setStatus({severity:'Approaching', …})` keinen neuen Status; `setStatus({severity:'Warning', …})` setzt ihn.
- Component-Test: Rendering pro Severity (richtige Farbe, richtiger Text, Fallback-Modell-Titel nur bei Warning).
- Dispatch-Test: SSE-Event `budget_status` ruft `setStatus` mit unveränderten Feldern auf.

## Akzeptanzkriterien

1. Bei Empfang eines `budget_status`-Events erscheint sichtbar ein Banner mit Period + Percentage.
2. Bei `severity === 'Warning'` zeigt das Banner zusätzlich `fallbackModelTitle`.
3. Nach Klick auf Dismiss verschwindet das Banner und gleiche Severity wird in dieser Session nicht mehr angezeigt.
4. Höhere Severity (z.B. Exhausted nach dismissed Approaching) wird wieder angezeigt.
5. Reload setzt Dismiss-State zurück.
6. Kein UI-Effekt für die alten Events `budget_warning`/`budget_exhausted` — diese existieren nicht mehr in der Spec.

## Out of Scope

- Anzeige des Banners außerhalb eines aktiven Chat-Sends (kein App-Start-Polling).
- Persistenter Dismiss über Reload hinweg.
- Tier-spezifische Farben/Texte über das Severity-Mapping hinaus.
