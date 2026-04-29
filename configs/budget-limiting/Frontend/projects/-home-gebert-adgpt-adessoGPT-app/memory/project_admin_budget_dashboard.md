---
name: Admin Budget Dashboard — Implementation Status
description: Control Center Budget Report page for admins — prototype implemented with summary cards + table + projection
type: project
originSessionId: e75bb576-5ea1-44f7-8dde-2f1fb0875f77
---
## Feature: Admin Budget Report im Control Center

**Status:** Prototyp implementiert und Build erfolgreich. Noch nicht gegen laufendes Backend getestet.

**Why:** Admins brauchen eine Ubersicht uber den Token-Verbrauch aller User mit Hochrechnungen und Filterung.

**How to apply:** Feature ist unter `/control-center/budget-report` erreichbar. Navigation unter "Administration" Gruppe.

## Implementierte Dateien

- `features/budget-report/budget-report.store.ts` — SignalStore mit API-Call, Projection, Summary
- `features/budget-report/budget-report.component.ts` + `.html` — Summary-Karten + Datentabelle
- Route in `lib.routes.ts`, Nav-Item in `navigation.component.html`
- i18n-Keys in allen 4 Sprachdateien (en/de/fr/it)

## Design-Entscheidungen

1. **Layout**: Kombination — Summary-Karten oben (Users, Tokens, Cost, Requests) + Datentabelle unten
2. **Projection**: Lineare Extrapolation clientseitig fur monatliche Eintrags
3. **Filter**: Period-Select (Monthly/Weekly/Daily/All) + Textsuche auf UserId
4. **Limit**: Keine Limit-Anzeige — nur Verbrauch

## Bekannte Lucken / Nachste Schritte

- Kein Gruppenfilter (braucht Backend-Support)
- Kein Username-Mapping (nur userId)
- Kein Token-Limit pro User sichtbar
- Projection nur fur monatliche Eintrags
- Paginierung: Aktuell PageSize 500, keine UI-Paginierung
- Noch kein Test gegen laufendes Backend
