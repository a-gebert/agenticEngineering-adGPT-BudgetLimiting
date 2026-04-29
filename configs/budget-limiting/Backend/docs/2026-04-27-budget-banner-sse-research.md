# Budget Banner — Backend → Frontend Push Mechanismen

**Datum:** 2026-04-27
**Branch:** feature/PBI3271_Budget_Limits
**Kontext:** Recherche für ein UI-Banner, das Nutzer bei 80% (Warnung) und 100% (Fallback-Info oder Sperre) ihres Budgets informiert.

---

## 1. Verfügbare Push-Mechanismen im Backend

| Mechanismus | Status | Geeignet für Budget-Banner? |
|---|---|---|
| **SSE (Chat-Streaming)** | aktiv produktiv | Ja, request-scoped (nur während Chat-Send) |
| **AppAlert** | global, manuell, kein User-Scope | Nur mit Erweiterung — Per-User-Targeting fehlt |
| **WebSocket (OpenAI Realtime)** | nur für Voice-I/O zur OpenAI | Nein — kein generischer App-Broadcast |
| SignalR / Long-Polling | nicht vorhanden | — |

### SSE — Chat-Streaming Pipeline
- Endpoint: `ChatStreamHttpResult.cs:20–43` schreibt jeden `ChatStreamResponse` als SSE-Frame (`event: <name>\ndata: <json>\n\n`).
- Discriminator: `ChatStreamResponse.event`-Property, polymorphe JSON-Serialisierung via `PolymorphicSerializeOnlyJsonConverter<ChatStreamResponse>`.
- Stream-Lebensdauer: pro Request — keine persistente Verbindung außerhalb eines aktiven Chat-Sends.

### AppAlert
- Entity: `Backend/Shared/adessoGPT.Domain/PersistedEntities/System/Settings/AppAlerts/AppAlert.cs` — Felder: `Id`, `Type` (Info/Warning/Error), `Message` (LocalizationStrings), `IsActive`. **Kein UserId/TargetUserId**.
- Endpoint: `GET /api/active-app-alerts` (public, unauth) — `AppAlertEndpoints.cs:16`.
- Admin-CRUD: `ControlCenterAppAlertEndpoints.cs` (Rolle `ControlCenterAdmin`).
- Persistenz: System-Container (Cosmos/Mongo), FusionCache.
- Frontend: nur React (`adessoGPT.UI/src/components/Header/AppAlerts.tsx`) — Angular hat OpenAPI-Client, aber **keine UI-Anbindung**.

---

## 2. Bereits implementierte Budget-Infrastruktur (Branch `feature/PBI3271_Budget_Limits`)

### SSE-Response-Typen (vorhanden)
`Backend/Shared/adessoGPT.Chat.Abstractions/Streaming/Updates/`:
- `ChatBudgetWarningResponse` — `event: "budget_warning"`, Felder `Message`, `FallbackModelTitle` (beide required)
- `ChatBudgetExhaustedResponse` — `event: "budget_exhausted"`, Feld `Message`

### `BudgetGuardService` (vorhanden)
`Backend/Application/adessoGPT.Application/Business/Budget/Services/BudgetGuardService.cs`

Public API:
- `CheckBudgetAsync(ChatStreamContext, CancellationToken)` → `BudgetCheckResult`
- `EnforceBudgetAsync(ChatStreamContext, ConversationId, Func rebuildContextAsync, CancellationToken)` → `Result<BudgetEnforcementResult>`

Outcomes (`BudgetCheckOutcome`):
- `Allowed` — alles okay
- `FallbackModel` — Limit erreicht, Agent hat `IsBudgetFallback`-Modell → `UpdateConversationModelCommand` + `ChatBudgetWarningResponse` published
- `Blocked` — Limit erreicht, kein Fallback → `ChatBudgetExhaustedResponse` published, Stream endet (`yield break`)

Periodencheck: `IsAnyPeriodExceededAsync` (Zeile 76–127) iteriert Daily/Weekly/Monthly und prüft `state.TokensUsed >= limit`.

**Wichtig: Keine 80%-Schwelle.** Logik triggert ausschließlich bei `>= limit` (100%).

### Aufrufstellen von `EnforceBudgetAsync`
Fünf Chat-Handler integrieren bereits den Guard:
- `StartChatConversationCommandHandler.cs:67`
- `ChangeUserChatMessageCommandHandler.cs:123`
- `RegenerateAssistantChatMessageCommandHandler.cs:111`
- `ResumeChatConversationCommandHandler.cs:138`
- `StartRealtimeChatConversationCommandHandler.cs:75` (Realtime/Voice)

### Wrapper-Chain & Token-Recording
DI-Registration in `ApplicationModule.cs`:
1. `ChatStreamDebounceWrapper` — Delta-Coalescing
2. `ChatStreamProgressMinimumDisplayWrapper` — Progress-Throttle
3. `ChatStreamPersistingWrapper` — Persistenz + `RecordChatBudgetUsageCommand` (`ChatStreamPersistingWrapper.cs:215–248`)
4. `ChatStreamKeepAliveWrapper`

Komposition: `CreateChatStreamQueryHandler.cs:60–67`.

Token-Recording-Punkt: `ChatStreamPersistingWrapper.TryRecordBudgetUsageAsync()` ruft `ITokenCounter.CountTokensWithFallbackModelAsDefault()` und sendet `RecordChatBudgetUsageCommand` **nach** dem Stream-Ende.

---

## 3. Frontend — Angular SSE-Konsument

### API-Service (vorhanden)
`Frontend/adessoGPT.Web/libs/chat/src/features/chat/shared/chat-stream-api.service.ts`

Liefert `AsyncGenerator<ChatStreamResponse>` aus dem auto-generierten HeyAPI-`createSseClient`. Discriminated Union ist über die generierten OpenAPI-Typen bereits korrekt typisiert.

### Event-Dispatch (Lücke)
`Frontend/adessoGPT.Web/libs/chat/src/features/chat/existing-chat/chat-stream.store.ts:235`

```typescript
switch (response.event) {
  case 'conversation_created': ...
  case 'delta': ...
  case 'citation': ...
  case 'reasoning_phase_started': ...
  case 'reasoning_delta': ...
  case 'reasoning_phase_completed': ...
  case 'reasoning_total_completed': ...
  case 'complete': ...
  case 'user_message_created': ...
  case 'error': ...
  case 'title_generation': ...
  default: store._appendResponse(currentKey, response);
}
```

`'budget_warning'` und `'budget_exhausted'` fallen in `default` → werden nur als Roh-Response abgelegt, **kein UI-Effekt**.

Realtime hat einen eigenen Dispatch in `realtime.store.ts:448` mit analoger Lücke.

---

## 4. Optionen für den Banner

### Option A — SSE-Stream erweitern (geringster Aufwand bei 100%)
**Backend:** schon da — keine Änderung nötig für 100%.
**Frontend:** zwei Cases (`'budget_warning'`, `'budget_exhausted'`) in `chat-stream.store.ts` ergänzen, Dispatch in einen neuen `BudgetBannerStore` (Signal-Store), Banner-Komponente in App-Shell.

**Einschränkungen:**
- Banner triggert nur bei aktivem Chat-Send. Wer die App öffnet und nichts schickt, sieht nichts.
- Nach Reload weg, bis nächste Nachricht das Event erneut sendet.
- Bei jedem Send über der Schwelle wird das Event erneut gesendet — Frontend muss „einmal pro Session anzeigen" oder „bei jedem Hit anzeigen" entscheiden.

### Option B — AppAlert per-User erweitern
**Backend-Änderungen:**
- `TargetUserId?` an `AppAlert` (nullable: null = global, gesetzt = per User)
- Public-Endpoint nach aktuellem User filtern
- Automatischer Emitter bei Schwellen-Übertritt
- Lifecycle: Alert beim Period-Reset entfernen

**Probleme:** Per-User-Daten im System-Container (eigentlich für globale Settings), Cache-Invalidierung per User, Sync-Aufwand zwischen Budget-State und Alert-Lifecycle.

### Option C — Abgeleiteter Banner-Endpoint
- `GET /api/me/budget-banner` liest `UserBudgetState` + Tier, berechnet `%`, liefert DTO oder null
- Frontend pollt beim App-Start / Routenwechsel
- Zustandslos, kein Storage, kein Cache-Problem
- Reset bei Period-Wechsel automatisch (weil abgeleitet)
- **Nachteil:** zweiter Datenfluss neben SSE

---

## 5. 80%-Schwelle — was fehlt

`BudgetGuardService` kennt heute nur `>= limit` (100%). Für 80%-Warnung:

**Backend:**
1. Neuer Outcome `BudgetCheckOutcome.ApproachingLimit` (oder Prozent-Feld am Result), getriggert bei `TokensUsed >= 0.8 * limit && < limit`.
2. Entweder neuer Response-Typ `ChatBudgetApproachingResponse` **oder** `ChatBudgetWarningResponse` um `Severity`/`Percentage` erweitern. **Aktuell hat `ChatBudgetWarningResponse.FallbackModelTitle` `required` Semantik für 100%-Fallback** — separater Typ ist sauberer.
3. Schwelle aus `BudgetLimitSettings` lesen (nicht hartcoden), damit Admins justieren können.

**Frontend:** dritter Case `'budget_approaching'` im Dispatch.

---

## 6. UX-Frage (offen)

Bei 100% mit Fallback-Modell: Banner soll informieren („Du läufst jetzt über das Fallback-Modell"), aber Chat funktioniert weiter.
Bei 100% ohne Fallback: Banner + Chat blockiert (heute schon implementiert via `BudgetCheckOutcome.Blocked`).

Frage: Soll bei 80%/100% **nur beim aktiven Send** informiert werden (SSE) oder **auch beim App-Start** (zusätzlicher Pull-Endpoint)?

Antwort beeinflusst: nur Option A vs. Option A + C kombiniert.

---

## 7. Empfehlung

- Für „nur beim Chat-Send sichtbar": **Option A** — Backend-Logik um 80%-Outcome + neuen Response-Typ erweitern, Frontend-Dispatch ergänzen.
- Für „auch beim App-Start sichtbar": **Option A + C** — SSE für Echtzeit-Hits während des Sends, Pull-Endpoint für persistente Sichtbarkeit.
- **Option B (AppAlert mit UserId)** wird nicht empfohlen — vermischt globale Admin-Banner und per-User-Budget-Status, Storage- und Cache-Komplexität ohne klaren Vorteil.
